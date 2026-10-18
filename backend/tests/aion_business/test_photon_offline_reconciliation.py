from __future__ import annotations

import base64
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.photon_billing_contracts import PhotonLedgerEntry
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_offline_lease import LEASE_SCHEMA, PhotonOfflineLeaseWallet
from backend.modules.aion_business.runtime.photon_offline_reconciliation import PhotonOfflineLeaseAuthority, PhotonOfflineReconciliationError


def pub(key):
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def setup(tmp_path):
    ledger = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    ledger.post(transaction_id="grant", tenant_id="tenant-1", reason="bundle_grant", source_receipt_id="purchase-1", rate_card_version="price-1", idempotency_key="grant", recorded_at="t0", entries=[PhotonLedgerEntry("platform.issued", -100), PhotonLedgerEntry("customer.available", 100)])
    authority_key, node_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    authority = PhotonOfflineLeaseAuthority(tmp_path / "leases.sqlite3", ledger=ledger, authority_private_key=authority_key)
    payload = {"schema_version": LEASE_SCHEMA, "lease_id": "lease-1", "tenant_id": "tenant-1", "node_id": "node-1", "sequence": 1, "photon_limit": 60, "valid_from": "2026-10-17T00:00:00+00:00", "valid_until": "2026-10-18T00:00:00+00:00", "price_book_version": "price-1"}
    envelope = authority.issue(payload, node_public_key=pub(node_key), recorded_at="t1")
    wallet = PhotonOfflineLeaseWallet(tmp_path / "wallet.sqlite3", lease=envelope, authority_public_key=authority_key.public_key(), tenant_id="tenant-1", node_id="node-1", now="2026-10-17T01:00:00+00:00")
    wallet.capture_success(receipt_id="receipt-1", action_type="invoice-created", photons=20, success_evidence_code="invoice-persisted", completed_at="2026-10-17T01:01:00+00:00", now="2026-10-17T01:01:00+00:00")
    return ledger, authority, node_key, wallet


def test_issue_reserves_and_reconcile_captures_exactly_once(tmp_path):
    ledger, authority, node, wallet = setup(tmp_path)
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 40
    report = wallet.signed_reconciliation(node_private_key=node)
    result = authority.reconcile(report, action_rates={"invoice-created": 20}, recorded_at="t2")
    replay = authority.reconcile(report, action_rates={"invoice-created": 20}, recorded_at="t2")
    assert result == replay
    assert ledger.balances(tenant_id="tenant-1")["platform.consumed"] == 20


def test_tamper_and_wrong_rate_fail_without_capture(tmp_path):
    ledger, authority, node, wallet = setup(tmp_path)
    report = wallet.signed_reconciliation(node_private_key=node)
    with pytest.raises(PhotonOfflineReconciliationError, match="rate_mismatch"):
        authority.reconcile(report, action_rates={"invoice-created": 21}, recorded_at="t2")
    report["payload"]["photons_used"] = 1
    with pytest.raises(PhotonOfflineReconciliationError, match="signature_invalid"):
        authority.reconcile(report, action_rates={"invoice-created": 20}, recorded_at="t2")
    assert "platform.consumed" not in ledger.balances(tenant_id="tenant-1")


def test_expired_lease_releases_unused_reservation_and_blocks_new_spend(tmp_path):
    ledger, authority, node, wallet = setup(tmp_path)
    authority.reconcile(
        wallet.signed_reconciliation(node_private_key=node),
        action_rates={"invoice-created": 20}, recorded_at="t2",
    )
    closed = authority.close_expired(
        "lease-1", now="2026-10-18T00:00:00+00:00", recorded_at="t3"
    )
    replay = authority.close_expired(
        "lease-1", now="2026-10-18T00:00:00+00:00", recorded_at="t3"
    )
    assert closed["photons_released"] == 40
    assert replay["photons_released"] == 40 and replay["replay"] is True
    assert ledger.balances(tenant_id="tenant-1")["customer.available"] == 80
    wallet.capture_success(
        receipt_id="receipt-2", action_type="invoice-created", photons=20,
        success_evidence_code="invoice-persisted", completed_at="2026-10-17T02:00:00+00:00",
        now="2026-10-17T02:00:00+00:00",
    )
    with pytest.raises(ValueError, match="protected_account_insufficient"):
        authority.reconcile(
            wallet.signed_reconciliation(node_private_key=node),
            action_rates={"invoice-created": 20}, recorded_at="t4",
        )


def test_report_spend_must_have_completed_inside_lease_window(tmp_path):
    _, authority, node, wallet = setup(tmp_path)
    wallet.capture_success(
        receipt_id="receipt-outside",
        action_type="invoice-created",
        photons=20,
        success_evidence_code="invoice-persisted",
        completed_at="2026-10-18T00:00:00+00:00",
        now="2026-10-17T02:00:00+00:00",
    )
    with pytest.raises(PhotonOfflineReconciliationError, match="outside_lease"):
        authority.reconcile(
            wallet.signed_reconciliation(node_private_key=node),
            action_rates={"invoice-created": 20},
            recorded_at="t2",
        )


def test_offline_authority_store_is_private_and_refuses_symlink(tmp_path):
    ledger, authority, _, _ = setup(tmp_path)
    assert os.stat(authority.database.parent).st_mode & 0o777 == 0o700
    assert os.stat(authority.database).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-leases.sqlite3"
    link.symlink_to(authority.database)
    with pytest.raises(
        PhotonOfflineReconciliationError, match="symlink_database_forbidden"
    ):
        PhotonOfflineLeaseAuthority(
            link,
            ledger=ledger,
            authority_private_key=Ed25519PrivateKey.generate(),
        )
