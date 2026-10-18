from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PHOTON_ASSET_NAMESPACE,
    WORK_RECEIPT_SCHEMA,
    canonical_bytes,
    canonical_hash,
)


OUTBOX_SCHEMA = "tessaris.photon-work-receipt-outbox.v1"
SIGNED_RECEIPT_SCHEMA = "tessaris.photon-signed-work-receipt.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
RECEIPT_FIELDS = {
    "schema_version", "asset_namespace", "receipt_id", "tenant_commitment",
    "device_id", "action_type", "outcome_id", "photons",
    "rate_card_version", "reservation_id", "billing_parent_id",
    "completed_at", "previous_receipt_hash", "success_evidence_code",
    "customer_content_included", "local_model_tokens_billed", "receipt_hash",
}
TERMINAL_STATES = frozenset({"acknowledged", "rejected"})


class PhotonWorkReceiptOutboxError(ValueError):
    pass


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _safe(value: str, field: str) -> str:
    result = str(value or "").strip()
    if not SAFE_ID.fullmatch(result):
        raise PhotonWorkReceiptOutboxError(f"{field}_invalid")
    return result


class PhotonWorkReceiptOutbox:
    """Immutable signed local receipt chain with an append-only delivery outbox."""

    def __init__(
        self,
        database: str | Path,
        *,
        tenant_commitment: str,
        device_id: str,
        device_private_key: Ed25519PrivateKey,
        max_pending: int = 10_000,
    ) -> None:
        if not isinstance(device_private_key, Ed25519PrivateKey):
            raise PhotonWorkReceiptOutboxError("device_private_key_invalid")
        candidate = Path(database).expanduser()
        if candidate.is_symlink():
            raise PhotonWorkReceiptOutboxError("receipt_outbox_symlink_database_forbidden")
        self.path = candidate.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self.tenant_commitment = _safe(tenant_commitment, "tenant_commitment")
        self.device_id = _safe(device_id, "device_id")
        self.private_key = device_private_key
        self.public_key_b64 = _b64(
            device_private_key.public_key().public_bytes_raw()
        )
        self.max_pending = int(max_pending)
        if not 1 <= self.max_pending <= 1_000_000:
            raise PhotonWorkReceiptOutboxError("outbox_limit_invalid")
        self._initialise()
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_work_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    tenant_commitment TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL UNIQUE,
                    previous_receipt_hash TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    device_public_key TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0)
                );
                CREATE TABLE IF NOT EXISTS photon_work_receipt_outbox_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    receipt_id TEXT NOT NULL REFERENCES photon_work_receipts(receipt_id),
                    state TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    remote_reference TEXT,
                    error_code TEXT,
                    schema_version TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0)
                );
                CREATE TRIGGER IF NOT EXISTS photon_work_receipts_no_update
                    BEFORE UPDATE ON photon_work_receipts
                    BEGIN SELECT RAISE(ABORT, 'photon_work_receipt_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_work_receipts_no_delete
                    BEFORE DELETE ON photon_work_receipts
                    BEGIN SELECT RAISE(ABORT, 'photon_work_receipt_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_work_receipt_events_no_update
                    BEFORE UPDATE ON photon_work_receipt_outbox_events
                    BEGIN SELECT RAISE(ABORT, 'photon_work_receipt_event_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_work_receipt_events_no_delete
                    BEFORE DELETE ON photon_work_receipt_outbox_events
                    BEGIN SELECT RAISE(ABORT, 'photon_work_receipt_event_immutable'); END;
                """
            )

    def enqueue(
        self, receipt: Mapping[str, Any], *, event_id: str, recorded_at: str
    ) -> dict[str, Any]:
        value = self._validated_receipt(receipt)
        event_id = _safe(event_id, "event_id")
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
        signature = _b64(self.private_key.sign(canonical_bytes(value)))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT receipt_json, signature, device_public_key FROM photon_work_receipts WHERE receipt_id = ?",
                    (value["receipt_id"],),
                ).fetchone()
                if existing:
                    if tuple(existing) != (encoded, signature, self.public_key_b64):
                        raise PhotonWorkReceiptOutboxError("receipt_id_collision")
                    connection.commit()
                    return self.receipt(value["receipt_id"])
                pending = int(connection.execute(
                    """
                    SELECT COUNT(*) FROM photon_work_receipts r
                    WHERE COALESCE((
                        SELECT e.state FROM photon_work_receipt_outbox_events e
                        WHERE e.receipt_id = r.receipt_id ORDER BY e.sequence DESC LIMIT 1
                    ), 'queued') NOT IN ('acknowledged', 'rejected')
                    """
                ).fetchone()[0])
                if pending >= self.max_pending:
                    raise PhotonWorkReceiptOutboxError("receipt_outbox_capacity_exceeded")
                last = connection.execute(
                    "SELECT receipt_hash FROM photon_work_receipts ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
                expected_previous = last["receipt_hash"] if last else "genesis"
                if value["previous_receipt_hash"] != expected_previous:
                    raise PhotonWorkReceiptOutboxError("receipt_chain_previous_hash_mismatch")
                connection.execute(
                    """
                    INSERT INTO photon_work_receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        value["receipt_id"], value["tenant_commitment"], value["device_id"],
                        value["receipt_hash"], value["previous_receipt_hash"], encoded,
                        signature, self.public_key_b64, recorded_at, SIGNED_RECEIPT_SCHEMA,
                    ),
                )
                self._append_event(
                    connection, event_id=event_id, receipt_id=value["receipt_id"],
                    state="queued", recorded_at=recorded_at,
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self.receipt(value["receipt_id"])

    def mark_submitted(
        self, receipt_id: str, *, event_id: str, batch_reference: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        return self._transition(
            receipt_id, event_id=event_id, state="submitted",
            remote_reference=batch_reference, error_code=None, recorded_at=recorded_at,
        )

    def mark_retry_pending(
        self, receipt_id: str, *, event_id: str, error_code: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        return self._transition(
            receipt_id, event_id=event_id, state="retry_pending",
            remote_reference=None, error_code=error_code, recorded_at=recorded_at,
        )

    def acknowledge(
        self, receipt_id: str, *, event_id: str, remote_receipt_reference: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        return self._transition(
            receipt_id, event_id=event_id, state="acknowledged",
            remote_reference=remote_receipt_reference, error_code=None,
            recorded_at=recorded_at,
        )

    def reject(
        self, receipt_id: str, *, event_id: str, error_code: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        return self._transition(
            receipt_id, event_id=event_id, state="rejected",
            remote_reference=None, error_code=error_code, recorded_at=recorded_at,
        )

    def _transition(
        self, receipt_id: str, *, event_id: str, state: str,
        remote_reference: str | None, error_code: str | None, recorded_at: str,
    ) -> dict[str, Any]:
        receipt_id = _safe(receipt_id, "receipt_id")
        event_id = _safe(event_id, "event_id")
        if state not in {"submitted", "retry_pending", "acknowledged", "rejected"}:
            raise PhotonWorkReceiptOutboxError("receipt_outbox_state_invalid")
        remote = _safe(remote_reference, "remote_reference") if remote_reference else None
        error = _safe(error_code, "error_code") if error_code else None
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if not connection.execute(
                    "SELECT 1 FROM photon_work_receipts WHERE receipt_id = ?", (receipt_id,)
                ).fetchone():
                    raise KeyError("work_receipt_not_found")
                current = self._latest_event(connection, receipt_id)
                if current["state"] in TERMINAL_STATES:
                    if (
                        current["event_id"], current["state"],
                        current["remote_reference"], current["error_code"],
                    ) == (event_id, state, remote, error):
                        connection.commit()
                        return self.receipt(receipt_id)
                    raise PhotonWorkReceiptOutboxError("receipt_outbox_terminal")
                self._append_event(
                    connection, event_id=event_id, receipt_id=receipt_id,
                    state=state, recorded_at=recorded_at,
                    remote_reference=remote, error_code=error,
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self.receipt(receipt_id)

    def pending(self, *, limit: int = 100) -> list[dict[str, Any]]:
        limit = int(limit)
        if not 1 <= limit <= 1000:
            raise PhotonWorkReceiptOutboxError("receipt_outbox_limit_invalid")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.receipt_id FROM photon_work_receipts r
                JOIN photon_work_receipt_outbox_events e ON e.sequence = (
                    SELECT MAX(latest.sequence) FROM photon_work_receipt_outbox_events latest
                    WHERE latest.receipt_id = r.receipt_id
                )
                WHERE e.state NOT IN ('acknowledged', 'rejected')
                ORDER BY e.sequence LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self.receipt(row["receipt_id"]) for row in rows]

    def receipt(self, receipt_id: str) -> dict[str, Any]:
        receipt_id = _safe(receipt_id, "receipt_id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM photon_work_receipts WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()
            if not row:
                raise KeyError("work_receipt_not_found")
            event = self._latest_event(connection, receipt_id)
        result = {
            "schema_version": SIGNED_RECEIPT_SCHEMA,
            "receipt": json.loads(row["receipt_json"]),
            "signature": row["signature"],
            "device_public_key": row["device_public_key"],
            "outbox": {
                "schema_version": OUTBOX_SCHEMA,
                "state": event["state"],
                "recorded_at": event["recorded_at"],
                "remote_reference": event["remote_reference"],
                "error_code": event["error_code"],
            },
            "customer_content_included": False,
            "local_model_tokens_billed": False,
        }
        self.verify(result)
        return result

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.state, COUNT(*) AS count
                FROM photon_work_receipts r
                JOIN photon_work_receipt_outbox_events e ON e.sequence = (
                    SELECT MAX(latest.sequence) FROM photon_work_receipt_outbox_events latest
                    WHERE latest.receipt_id = r.receipt_id
                ) GROUP BY e.state ORDER BY e.state
                """
            ).fetchall()
            total = int(connection.execute(
                "SELECT COUNT(*) FROM photon_work_receipts"
            ).fetchone()[0])
        counts = {row["state"]: int(row["count"]) for row in rows}
        return {
            "schema_version": OUTBOX_SCHEMA,
            "receipt_count": total,
            "state_counts": counts,
            "pending_count": sum(
                count for state, count in counts.items() if state not in TERMINAL_STATES
            ),
            "customer_content_included": False,
            "local_model_tokens_billed": False,
        }

    def verify(self, envelope: Mapping[str, Any]) -> bool:
        receipt = dict(envelope.get("receipt") or {})
        try:
            Ed25519PublicKey.from_public_bytes(
                _unb64(str(envelope.get("device_public_key") or ""))
            ).verify(
                _unb64(str(envelope.get("signature") or "")), canonical_bytes(receipt)
            )
        except (InvalidSignature, ValueError) as exc:
            raise PhotonWorkReceiptOutboxError("work_receipt_signature_invalid") from exc
        self._validated_receipt(receipt)
        return True

    def _validated_receipt(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        value = dict(receipt)
        if set(value) != RECEIPT_FIELDS:
            raise PhotonWorkReceiptOutboxError("work_receipt_fields_invalid")
        if value.get("schema_version") != WORK_RECEIPT_SCHEMA:
            raise PhotonWorkReceiptOutboxError("work_receipt_schema_invalid")
        if value.get("asset_namespace") != PHOTON_ASSET_NAMESPACE:
            raise PhotonWorkReceiptOutboxError("work_receipt_asset_invalid")
        if value.get("customer_content_included") is not False:
            raise PhotonWorkReceiptOutboxError("work_receipt_content_prohibited")
        if value.get("local_model_tokens_billed") is not False:
            raise PhotonWorkReceiptOutboxError("work_receipt_model_tokens_prohibited")
        if value.get("tenant_commitment") != self.tenant_commitment:
            raise PhotonWorkReceiptOutboxError("work_receipt_tenant_mismatch")
        if value.get("device_id") != self.device_id:
            raise PhotonWorkReceiptOutboxError("work_receipt_device_mismatch")
        supplied_hash = str(value.pop("receipt_hash") or "")
        if supplied_hash != canonical_hash(value):
            raise PhotonWorkReceiptOutboxError("work_receipt_hash_invalid")
        value["receipt_hash"] = supplied_hash
        return value

    @staticmethod
    def _latest_event(connection: sqlite3.Connection, receipt_id: str) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT * FROM photon_work_receipt_outbox_events
            WHERE receipt_id = ? ORDER BY sequence DESC LIMIT 1
            """,
            (receipt_id,),
        ).fetchone()
        if not row:
            raise RuntimeError("work_receipt_outbox_event_missing")
        return row

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection, *, event_id: str, receipt_id: str,
        state: str, recorded_at: str, remote_reference: str | None = None,
        error_code: str | None = None,
    ) -> None:
        existing = connection.execute(
            """
            SELECT receipt_id, state, recorded_at, remote_reference, error_code
            FROM photon_work_receipt_outbox_events WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()
        candidate = (receipt_id, state, recorded_at, remote_reference, error_code)
        if existing:
            if tuple(existing) != candidate:
                raise PhotonWorkReceiptOutboxError("receipt_outbox_event_collision")
            return
        connection.execute(
            """
            INSERT INTO photon_work_receipt_outbox_events (
                event_id, receipt_id, state, recorded_at, remote_reference,
                error_code, schema_version, customer_content_included
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (event_id, *candidate, OUTBOX_SCHEMA),
        )
