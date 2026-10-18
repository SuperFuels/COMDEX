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

from backend.modules.aion_business.runtime.photon_billing_contracts import canonical_bytes
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore


WALLET_SNAPSHOT_SCHEMA = "tessaris.photon-wallet-snapshot.v1"
SNAPSHOT_FIELDS = {
    "schema_version", "tenant_id", "sequence", "available_photons",
    "reserved_photons", "lifetime_consumed_photons", "ledger_transaction_count",
    "ledger_anchor", "issued_at", "valid_until", "customer_content_included",
    "local_model_tokens_billed",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
MAX_SNAPSHOT_LIFETIME_SECONDS = 3600


class PhotonWalletSnapshotError(ValueError):
    pass


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PhotonWalletSnapshotError("wallet_snapshot_timezone_required")
    return parsed.astimezone(UTC)


class PhotonWalletSnapshotAuthority:
    """Issue immutable short-lived wallet views from the authoritative hosted ledger."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        ledger: PhotonLedgerStore,
        authority_private_key: Ed25519PrivateKey,
    ) -> None:
        candidate = Path(database_path).expanduser()
        if candidate.is_symlink():
            raise PhotonWalletSnapshotError("wallet_snapshot_symlink_database_forbidden")
        self.path = candidate.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self.ledger = ledger
        self.private_key = authority_private_key
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_wallet_snapshots (
                    tenant_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL CHECK (sequence > 0),
                    payload_json TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, sequence)
                );
                CREATE TRIGGER IF NOT EXISTS photon_wallet_snapshots_no_update
                    BEFORE UPDATE ON photon_wallet_snapshots
                    BEGIN SELECT RAISE(ABORT, 'photon_wallet_snapshot_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_wallet_snapshots_no_delete
                    BEFORE DELETE ON photon_wallet_snapshots
                    BEGIN SELECT RAISE(ABORT, 'photon_wallet_snapshot_immutable'); END;
                """
            )
        os.chmod(self.path, 0o600)

    def _connect(self, *, isolation_level: str | None = "") -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path, timeout=30, isolation_level=isolation_level
        )
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def issue(self, *, tenant_id: str, issued_at: str, valid_until: str) -> dict[str, Any]:
        if not SAFE_ID.fullmatch(str(tenant_id or "")):
            raise PhotonWalletSnapshotError("wallet_snapshot_tenant_invalid")
        lifetime = (_time(valid_until) - _time(issued_at)).total_seconds()
        if lifetime <= 0 or lifetime > MAX_SNAPSHOT_LIFETIME_SECONDS:
            raise PhotonWalletSnapshotError("wallet_snapshot_period_invalid")
        state = self.ledger.wallet_state(tenant_id=tenant_id)
        if any(
            int(state[field]) < 0
            for field in ("available_photons", "reserved_photons", "lifetime_consumed_photons")
        ):
            raise PhotonWalletSnapshotError("wallet_snapshot_negative_balance")
        with self._connect(isolation_level=None) as connection:
            connection.execute("BEGIN IMMEDIATE")
            sequence = int(connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM photon_wallet_snapshots WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()[0])
            payload = {
                "schema_version": WALLET_SNAPSHOT_SCHEMA,
                "tenant_id": tenant_id,
                "sequence": sequence,
                "available_photons": state["available_photons"],
                "reserved_photons": state["reserved_photons"],
                "lifetime_consumed_photons": state["lifetime_consumed_photons"],
                "ledger_transaction_count": state["ledger_transaction_count"],
                "ledger_anchor": state["ledger_anchor"],
                "issued_at": issued_at,
                "valid_until": valid_until,
                "customer_content_included": False,
                "local_model_tokens_billed": False,
            }
            signature = _b64(self.private_key.sign(canonical_bytes(payload)))
            connection.execute(
                "INSERT INTO photon_wallet_snapshots VALUES (?, ?, ?, ?)",
                (
                    tenant_id, sequence,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")), signature,
                ),
            )
            connection.commit()
        return {"payload": payload, "signature": signature}


def verify_wallet_snapshot(
    envelope: Mapping[str, Any],
    *,
    authority_public_key: Ed25519PublicKey,
    expected_tenant_id: str,
    now: str,
    minimum_sequence: int = 0,
) -> dict[str, Any]:
    payload = dict(envelope.get("payload") or {})
    if set(payload) != SNAPSHOT_FIELDS or payload.get("schema_version") != WALLET_SNAPSHOT_SCHEMA:
        raise PhotonWalletSnapshotError("wallet_snapshot_fields_invalid")
    try:
        authority_public_key.verify(
            _unb64(str(envelope.get("signature") or "")), canonical_bytes(payload)
        )
    except (InvalidSignature, ValueError) as exc:
        raise PhotonWalletSnapshotError("wallet_snapshot_signature_invalid") from exc
    if payload.get("tenant_id") != expected_tenant_id:
        raise PhotonWalletSnapshotError("wallet_snapshot_tenant_mismatch")
    if payload.get("customer_content_included") is not False or payload.get("local_model_tokens_billed") is not False:
        raise PhotonWalletSnapshotError("wallet_snapshot_content_prohibited")
    if not SAFE_ID.fullmatch(str(payload.get("tenant_id") or "")):
        raise PhotonWalletSnapshotError("wallet_snapshot_tenant_invalid")
    if int(payload.get("sequence") or 0) <= int(minimum_sequence):
        raise PhotonWalletSnapshotError("wallet_snapshot_replay_or_rollback")
    lifetime = (_time(payload["valid_until"]) - _time(payload["issued_at"])).total_seconds()
    if lifetime <= 0 or lifetime > MAX_SNAPSHOT_LIFETIME_SECONDS:
        raise PhotonWalletSnapshotError("wallet_snapshot_period_invalid")
    if _time(now) < _time(payload["issued_at"]) or _time(now) >= _time(payload["valid_until"]):
        raise PhotonWalletSnapshotError("wallet_snapshot_not_current")
    numeric = (
        "available_photons", "reserved_photons", "lifetime_consumed_photons",
        "ledger_transaction_count",
    )
    if any(int(payload.get(field) or 0) < 0 for field in numeric):
        raise PhotonWalletSnapshotError("wallet_snapshot_balance_invalid")
    anchor = str(payload.get("ledger_anchor") or "")
    if len(anchor) != 64 or any(char not in "0123456789abcdef" for char in anchor):
        raise PhotonWalletSnapshotError("wallet_snapshot_anchor_invalid")
    return payload
