from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend.modules.aion_business.runtime.photon_billing_contracts import PhotonLedgerEntry, canonical_bytes
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_offline_lease import (
    SAFE_ID, _time, _unb64, issue_offline_lease,
)


class PhotonOfflineReconciliationError(ValueError):
    pass


class PhotonOfflineLeaseAuthority:
    """Hosted lease reservation and exact-once content-free reconciliation boundary."""

    def __init__(
        self, database: str | Path, *, ledger: PhotonLedgerStore,
        authority_private_key: Ed25519PrivateKey,
    ) -> None:
        candidate = Path(database).expanduser()
        if candidate.is_symlink():
            raise PhotonOfflineReconciliationError(
                "offline_authority_symlink_database_forbidden"
            )
        self.database = candidate.resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.database.parent, 0o700)
        self.ledger = ledger
        self.authority_private_key = authority_private_key
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_offline_leases (
                    lease_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, node_id TEXT NOT NULL,
                    node_public_key TEXT NOT NULL, envelope_json TEXT NOT NULL,
                    price_book_version TEXT NOT NULL, photon_limit INTEGER NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS photon_offline_leases_no_update
                    BEFORE UPDATE ON photon_offline_leases BEGIN SELECT RAISE(ABORT, 'offline_lease_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_offline_leases_no_delete
                    BEFORE DELETE ON photon_offline_leases BEGIN SELECT RAISE(ABORT, 'offline_lease_immutable'); END;
                """
            )
        os.chmod(self.database, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def issue(self, payload: Mapping[str, Any], *, node_public_key: str, recorded_at: str) -> dict[str, Any]:
        envelope = issue_offline_lease(payload, authority_private_key=self.authority_private_key)
        lease = envelope["payload"]
        try:
            if len(_unb64(node_public_key)) != 32:
                raise ValueError
        except Exception as exc:
            raise PhotonOfflineReconciliationError("offline_node_public_key_invalid") from exc
        account = f"offline.{lease['lease_id']}.reserved"
        if self.ledger.balances(tenant_id=lease["tenant_id"]).get("customer.available", 0) < int(lease["photon_limit"]):
            raise PhotonOfflineReconciliationError("offline_lease_balance_insufficient")
        self.ledger.post(
            transaction_id=f"offline-lease:{lease['lease_id']}", tenant_id=lease["tenant_id"],
            reason="offline_lease_reservation", source_receipt_id=lease["lease_id"],
            rate_card_version=lease["price_book_version"], idempotency_key=f"offline-lease:{lease['lease_id']}",
            recorded_at=recorded_at,
            entries=[PhotonLedgerEntry("customer.available", -int(lease["photon_limit"])), PhotonLedgerEntry(account, int(lease["photon_limit"]))],
            nonnegative_accounts=["customer.available"],
        )
        encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            prior = connection.execute("SELECT envelope_json, node_public_key FROM photon_offline_leases WHERE lease_id = ?", (lease["lease_id"],)).fetchone()
            if prior and tuple(prior) != (encoded, node_public_key):
                raise PhotonOfflineReconciliationError("offline_lease_id_collision")
            if not prior:
                connection.execute(
                    "INSERT INTO photon_offline_leases VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (lease["lease_id"], lease["tenant_id"], lease["node_id"], node_public_key, encoded, lease["price_book_version"], int(lease["photon_limit"])),
                )
        return envelope

    def reconcile(self, report: Mapping[str, Any], *, action_rates: Mapping[str, int], recorded_at: str) -> dict[str, Any]:
        payload = dict(report.get("payload") or {})
        lease_id = str(payload.get("lease_id") or "")
        with self._connect() as connection:
            row = connection.execute("SELECT tenant_id, node_id, node_public_key, envelope_json, price_book_version, photon_limit FROM photon_offline_leases WHERE lease_id = ?", (lease_id,)).fetchone()
        if not row:
            raise PhotonOfflineReconciliationError("offline_lease_unknown")
        tenant_id, node_id, node_public_key, envelope_json, price_book_version, photon_limit = row
        lease = json.loads(envelope_json)["payload"]
        required = {"schema_version", "lease_id", "tenant_id", "node_id", "sequence", "price_book_version", "photon_limit", "photons_used", "spends", "customer_content_included", "local_model_tokens_billed"}
        if set(payload) != required or payload.get("schema_version") != "tessaris.photon-offline-reconciliation.v1":
            raise PhotonOfflineReconciliationError("offline_report_fields_invalid")
        if (payload.get("tenant_id"), payload.get("node_id"), payload.get("sequence"), payload.get("price_book_version"), payload.get("photon_limit")) != (tenant_id, node_id, lease["sequence"], price_book_version, photon_limit):
            raise PhotonOfflineReconciliationError("offline_report_identity_mismatch")
        if payload.get("customer_content_included") is not False or payload.get("local_model_tokens_billed") is not False:
            raise PhotonOfflineReconciliationError("offline_report_content_prohibited")
        try:
            Ed25519PublicKey.from_public_bytes(_unb64(node_public_key)).verify(_unb64(str(report.get("signature") or "")), canonical_bytes(payload))
        except (InvalidSignature, ValueError) as exc:
            raise PhotonOfflineReconciliationError("offline_report_signature_invalid") from exc
        spends = list(payload.get("spends") or [])
        if len({spend.get("receipt_id") for spend in spends}) != len(spends):
            raise PhotonOfflineReconciliationError("offline_report_duplicate_receipt")
        total = 0
        for spend in spends:
            if set(spend) != {"receipt_id", "action_type", "photons", "success_evidence_code", "completed_at"}:
                raise PhotonOfflineReconciliationError("offline_report_spend_fields_invalid")
            if not all(SAFE_ID.fullmatch(str(spend.get(field) or "")) for field in ("receipt_id", "action_type", "success_evidence_code")):
                raise PhotonOfflineReconciliationError("offline_report_spend_identity_invalid")
            action = str(spend.get("action_type") or "")
            photons = int(spend.get("photons") or 0)
            if action not in action_rates or photons != int(action_rates[action]) or photons <= 0:
                raise PhotonOfflineReconciliationError("offline_report_rate_mismatch")
            completed = _time(str(spend.get("completed_at") or ""))
            if completed < _time(lease["valid_from"]) or completed >= _time(
                lease["valid_until"]
            ):
                raise PhotonOfflineReconciliationError(
                    "offline_report_spend_outside_lease"
                )
            total += photons
        if total != int(payload.get("photons_used") or 0) or total > int(photon_limit):
            raise PhotonOfflineReconciliationError("offline_report_total_invalid")
        transactions = []
        for spend in spends:
            photons = int(spend["photons"])
            receipt_id = str(spend.get("receipt_id") or "")
            transactions.append(self.ledger.post(
                transaction_id=f"offline-spend:{lease_id}:{receipt_id}", tenant_id=tenant_id,
                reason="offline_verified_outcome_capture", source_receipt_id=receipt_id,
                rate_card_version=price_book_version, idempotency_key=f"offline-spend:{lease_id}:{receipt_id}",
                recorded_at=str(spend["completed_at"]),
                entries=[PhotonLedgerEntry(f"offline.{lease_id}.reserved", -photons), PhotonLedgerEntry("platform.consumed", photons)],
                nonnegative_accounts=[f"offline.{lease_id}.reserved"],
            ))
        return {"lease_id": lease_id, "reconciled_spend_count": len(transactions), "photons_reconciled": total, "content_free": True}

    def close_expired(self, lease_id: str, *, now: str, recorded_at: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT tenant_id, envelope_json, price_book_version FROM photon_offline_leases WHERE lease_id = ?",
                (lease_id,),
            ).fetchone()
        if not row:
            raise PhotonOfflineReconciliationError("offline_lease_unknown")
        tenant_id, envelope_json, price_book_version = row
        lease = json.loads(envelope_json)["payload"]
        if _time(now) < _time(lease["valid_until"]):
            raise PhotonOfflineReconciliationError("offline_lease_not_expired")
        account = f"offline.{lease_id}.reserved"
        transaction_id = f"offline-close:{lease_id}"
        try:
            prior_close = self.ledger.transaction(transaction_id)
        except KeyError:
            prior_close = None
        if prior_close:
            released = next(
                int(entry["quantity_photons"])
                for entry in prior_close["entries"]
                if entry["account"] == "customer.available"
            )
            return {
                "lease_id": lease_id, "photons_released": released,
                "closed": True, "replay": True, "content_free": True,
            }
        remaining = self.ledger.balances(tenant_id=tenant_id).get(account, 0)
        if remaining < 0:
            raise RuntimeError("offline_lease_balance_corrupt")
        if remaining:
            self.ledger.post(
                transaction_id=transaction_id, tenant_id=tenant_id,
                reason="offline_lease_unused_release", source_receipt_id=lease_id,
                rate_card_version=price_book_version, idempotency_key=f"offline-close:{lease_id}",
                recorded_at=recorded_at,
                entries=[PhotonLedgerEntry(account, -remaining), PhotonLedgerEntry("customer.available", remaining)],
                nonnegative_accounts=[account],
            )
        return {
            "lease_id": lease_id, "photons_released": remaining,
            "closed": True, "replay": False, "content_free": True,
        }
