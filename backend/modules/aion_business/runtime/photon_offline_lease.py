from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


LEASE_SCHEMA = "tessaris.photon-offline-lease.v1"
SPEND_SCHEMA = "tessaris.photon-offline-spend.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LEASE_KEYS = {
    "schema_version", "lease_id", "tenant_id", "node_id", "sequence",
    "photon_limit", "valid_from", "valid_until", "price_book_version",
}
MAX_OFFLINE_LEASE_SECONDS = 7 * 24 * 60 * 60
MAX_OFFLINE_LEASE_PHOTONS = 1_000_000_000


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("photon_lease_timezone_required")
    return parsed.astimezone(UTC)


class PhotonOfflineLeaseError(ValueError):
    pass


def _validated_lease_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    if set(value) != LEASE_KEYS or value.get("schema_version") != LEASE_SCHEMA:
        raise PhotonOfflineLeaseError("photon_lease_fields_invalid")
    if not all(
        SAFE_ID.fullmatch(str(value.get(field) or ""))
        for field in ("lease_id", "tenant_id", "node_id", "price_book_version")
    ):
        raise PhotonOfflineLeaseError("photon_lease_identity_invalid")
    sequence = int(value.get("sequence") or 0)
    limit = int(value.get("photon_limit") or 0)
    if sequence <= 0 or not 1 <= limit <= MAX_OFFLINE_LEASE_PHOTONS:
        raise PhotonOfflineLeaseError("photon_lease_limit_invalid")
    duration = (_time(value["valid_until"]) - _time(value["valid_from"])).total_seconds()
    if duration <= 0 or duration > MAX_OFFLINE_LEASE_SECONDS:
        raise PhotonOfflineLeaseError("photon_lease_period_invalid")
    return value


def issue_offline_lease(
    payload: Mapping[str, Any], *, authority_private_key: Ed25519PrivateKey
) -> dict[str, Any]:
    value = _validated_lease_payload(payload)
    return {"payload": value, "signature": _b64(authority_private_key.sign(_canonical(value)))}


def verify_offline_lease(
    envelope: Mapping[str, Any], *, authority_public_key: Ed25519PublicKey, now: str,
    expected_tenant_id: str, expected_node_id: str,
) -> dict[str, Any]:
    payload = dict(envelope.get("payload") or {})
    if set(payload) != LEASE_KEYS or payload.get("schema_version") != LEASE_SCHEMA:
        raise PhotonOfflineLeaseError("photon_lease_fields_invalid")
    try:
        authority_public_key.verify(_unb64(str(envelope.get("signature") or "")), _canonical(payload))
    except (InvalidSignature, ValueError) as exc:
        raise PhotonOfflineLeaseError("photon_lease_signature_invalid") from exc
    payload = _validated_lease_payload(payload)
    if payload.get("tenant_id") != expected_tenant_id or payload.get("node_id") != expected_node_id:
        raise PhotonOfflineLeaseError("photon_lease_identity_mismatch")
    if _time(now) < _time(payload["valid_from"]) or _time(now) >= _time(payload["valid_until"]):
        raise PhotonOfflineLeaseError("photon_lease_not_current")
    return payload


class PhotonOfflineLeaseWallet:
    """Local bounded lease journal; successful outcomes only, no model-token fields."""

    def __init__(
        self,
        database: str | Path,
        *,
        lease: Mapping[str, Any],
        authority_public_key: Ed25519PublicKey,
        tenant_id: str,
        node_id: str,
        now: str,
    ) -> None:
        self.lease = verify_offline_lease(
            lease, authority_public_key=authority_public_key, now=now,
            expected_tenant_id=tenant_id, expected_node_id=node_id,
        )
        candidate = Path(database).expanduser()
        if candidate.is_symlink():
            raise PhotonOfflineLeaseError("photon_offline_symlink_database_forbidden")
        self.database = candidate.resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.database.parent, 0o700)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_offline_spends (
                    lease_id TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    photons INTEGER NOT NULL CHECK (photons > 0),
                    success_evidence_code TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    PRIMARY KEY (lease_id, receipt_id)
                );
                CREATE TRIGGER IF NOT EXISTS photon_offline_spends_no_update
                    BEFORE UPDATE ON photon_offline_spends BEGIN SELECT RAISE(ABORT, 'offline_spend_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_offline_spends_no_delete
                    BEFORE DELETE ON photon_offline_spends BEGIN SELECT RAISE(ABORT, 'offline_spend_immutable'); END;
                """
            )
        os.chmod(self.database, 0o600)

    def _connect(self, *, isolation_level: str | None = "") -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database, timeout=30, isolation_level=isolation_level
        )
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def capture_success(
        self,
        *,
        receipt_id: str,
        action_type: str,
        photons: int,
        success_evidence_code: str,
        completed_at: str,
        now: str,
    ) -> dict[str, Any]:
        if _time(now) < _time(self.lease["valid_from"]) or _time(now) >= _time(self.lease["valid_until"]):
            raise PhotonOfflineLeaseError("photon_lease_not_current")
        if not all(SAFE_ID.fullmatch(str(value or "")) for value in (receipt_id, action_type, success_evidence_code)):
            raise PhotonOfflineLeaseError("photon_offline_spend_identity_invalid")
        photons = int(photons)
        if photons <= 0:
            raise PhotonOfflineLeaseError("photon_offline_spend_invalid")
        with self._connect(isolation_level=None) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT action_type, photons, success_evidence_code, completed_at FROM photon_offline_spends WHERE lease_id = ? AND receipt_id = ?",
                (self.lease["lease_id"], receipt_id),
            ).fetchone()
            operation = (action_type, photons, success_evidence_code, completed_at)
            if existing:
                if tuple(existing) != operation:
                    connection.rollback()
                    raise PhotonOfflineLeaseError("photon_offline_spend_collision")
                connection.commit()
                return self.status(idempotent_replay=True)
            used = int(connection.execute(
                "SELECT COALESCE(SUM(photons), 0) FROM photon_offline_spends WHERE lease_id = ?",
                (self.lease["lease_id"],),
            ).fetchone()[0])
            if used + photons > int(self.lease["photon_limit"]):
                connection.rollback()
                raise PhotonOfflineLeaseError("photon_offline_lease_exhausted")
            connection.execute(
                "INSERT INTO photon_offline_spends VALUES (?, ?, ?, ?, ?, ?)",
                (self.lease["lease_id"], receipt_id, action_type, photons, success_evidence_code, completed_at),
            )
            connection.commit()
        return self.status(idempotent_replay=False)

    def status(self, *, idempotent_replay: bool = False) -> dict[str, Any]:
        with self._connect() as connection:
            used = int(connection.execute(
                "SELECT COALESCE(SUM(photons), 0) FROM photon_offline_spends WHERE lease_id = ?",
                (self.lease["lease_id"],),
            ).fetchone()[0])
        limit = int(self.lease["photon_limit"])
        return {
            "schema_version": SPEND_SCHEMA,
            "lease_id": self.lease["lease_id"],
            "sequence": int(self.lease["sequence"]),
            "photon_limit": limit,
            "photons_used": used,
            "photons_remaining": limit - used,
            "idempotent_replay": idempotent_replay,
            "content_free": True,
        }

    def signed_reconciliation(self, *, node_private_key: Ed25519PrivateKey) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT receipt_id, action_type, photons, success_evidence_code, completed_at FROM photon_offline_spends WHERE lease_id = ? ORDER BY receipt_id",
                (self.lease["lease_id"],),
            ).fetchall()
        spends = [
            {
                "receipt_id": row[0], "action_type": row[1], "photons": int(row[2]),
                "success_evidence_code": row[3], "completed_at": row[4],
            }
            for row in rows
        ]
        payload = {
            "schema_version": "tessaris.photon-offline-reconciliation.v1",
            "lease_id": self.lease["lease_id"], "tenant_id": self.lease["tenant_id"],
            "node_id": self.lease["node_id"], "sequence": int(self.lease["sequence"]),
            "price_book_version": self.lease["price_book_version"],
            "photon_limit": int(self.lease["photon_limit"]),
            "photons_used": sum(row["photons"] for row in spends), "spends": spends,
            "customer_content_included": False, "local_model_tokens_billed": False,
        }
        return {"payload": payload, "signature": _b64(node_private_key.sign(_canonical(payload)))}
