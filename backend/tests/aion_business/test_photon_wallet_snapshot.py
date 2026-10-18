from __future__ import annotations

import base64
import os

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedgerEntry,
    canonical_bytes,
)
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_wallet_snapshot import (
    PhotonWalletSnapshotAuthority,
    PhotonWalletSnapshotError,
    verify_wallet_snapshot,
)


def setup(tmp_path):
    ledger = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    ledger.post(
        transaction_id="grant-1", tenant_id="tenant-1", reason="bundle_grant",
        source_receipt_id="purchase-1", rate_card_version="v1",
        idempotency_key="grant-1", recorded_at="2026-10-17T20:00:00Z",
        entries=[
            PhotonLedgerEntry("platform.grant-liability", -100),
            PhotonLedgerEntry("customer.available", 100),
        ],
    )
    key = Ed25519PrivateKey.generate()
    authority = PhotonWalletSnapshotAuthority(
        tmp_path / "snapshots.sqlite3", ledger=ledger, authority_private_key=key
    )
    return ledger, key, authority


def issue(authority):
    return authority.issue(
        tenant_id="tenant-1", issued_at="2026-10-17T21:00:00Z",
        valid_until="2026-10-17T22:00:00Z",
    )


def test_signed_snapshot_contains_only_content_free_authoritative_wallet_state(tmp_path):
    _, key, authority = setup(tmp_path)
    payload = verify_wallet_snapshot(
        issue(authority), authority_public_key=key.public_key(),
        expected_tenant_id="tenant-1", now="2026-10-17T21:30:00Z",
    )
    assert payload["available_photons"] == 100
    assert payload["reserved_photons"] == 0
    assert payload["ledger_transaction_count"] == 1
    assert payload["customer_content_included"] is False
    assert payload["local_model_tokens_billed"] is False


def test_tamper_wrong_tenant_expiry_and_rollback_are_rejected(tmp_path):
    _, key, authority = setup(tmp_path)
    envelope = issue(authority)
    envelope["payload"]["available_photons"] = 1000
    with pytest.raises(PhotonWalletSnapshotError, match="signature_invalid"):
        verify_wallet_snapshot(
            envelope, authority_public_key=key.public_key(),
            expected_tenant_id="tenant-1", now="2026-10-17T21:30:00Z",
        )
    valid = issue(authority)
    with pytest.raises(PhotonWalletSnapshotError, match="tenant_mismatch"):
        verify_wallet_snapshot(
            valid, authority_public_key=key.public_key(),
            expected_tenant_id="tenant-2", now="2026-10-17T21:30:00Z",
        )
    with pytest.raises(PhotonWalletSnapshotError, match="not_current"):
        verify_wallet_snapshot(
            valid, authority_public_key=key.public_key(),
            expected_tenant_id="tenant-1", now="2026-10-17T22:00:00Z",
        )
    with pytest.raises(PhotonWalletSnapshotError, match="replay_or_rollback"):
        verify_wallet_snapshot(
            valid, authority_public_key=key.public_key(),
            expected_tenant_id="tenant-1", now="2026-10-17T21:30:00Z",
            minimum_sequence=valid["payload"]["sequence"],
        )


def test_new_ledger_history_changes_anchor_and_snapshot_sequence(tmp_path):
    ledger, key, authority = setup(tmp_path)
    first = issue(authority)
    ledger.post(
        transaction_id="spend-1", tenant_id="tenant-1", reason="verified_outcome_capture",
        source_receipt_id="outcome-1", rate_card_version="v1",
        idempotency_key="spend-1", recorded_at="2026-10-17T21:10:00Z",
        entries=[
            PhotonLedgerEntry("customer.available", -20),
            PhotonLedgerEntry("platform.consumed", 20),
        ], nonnegative_accounts=["customer.available"],
    )
    second = authority.issue(
        tenant_id="tenant-1", issued_at="2026-10-17T21:15:00Z",
        valid_until="2026-10-17T22:15:00Z",
    )
    payload = verify_wallet_snapshot(
        second, authority_public_key=key.public_key(), expected_tenant_id="tenant-1",
        now="2026-10-17T21:30:00Z", minimum_sequence=first["payload"]["sequence"],
    )
    assert payload["sequence"] == first["payload"]["sequence"] + 1
    assert payload["available_photons"] == 80
    assert payload["lifetime_consumed_photons"] == 20
    assert payload["ledger_anchor"] != first["payload"]["ledger_anchor"]


def test_snapshot_lifetime_is_bounded_and_verifier_checks_it_independently(tmp_path):
    _, key, authority = setup(tmp_path)
    with pytest.raises(PhotonWalletSnapshotError, match="period_invalid"):
        authority.issue(
            tenant_id="tenant-1",
            issued_at="2026-10-17T21:00:00Z",
            valid_until="2026-10-17T22:00:01Z",
        )
    envelope = issue(authority)
    envelope["payload"]["valid_until"] = "2026-10-17T23:00:00Z"
    envelope["signature"] = base64.urlsafe_b64encode(
        key.sign(canonical_bytes(envelope["payload"]))
    ).decode("ascii").rstrip("=")
    with pytest.raises(PhotonWalletSnapshotError, match="period_invalid"):
        verify_wallet_snapshot(
            envelope,
            authority_public_key=key.public_key(),
            expected_tenant_id="tenant-1",
            now="2026-10-17T21:30:00Z",
        )


def test_snapshot_store_is_private_and_refuses_symlink(tmp_path):
    ledger, key, authority = setup(tmp_path)
    assert os.stat(authority.path.parent).st_mode & 0o777 == 0o700
    assert os.stat(authority.path).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-snapshots.sqlite3"
    link.symlink_to(authority.path)
    with pytest.raises(PhotonWalletSnapshotError, match="symlink_database_forbidden"):
        PhotonWalletSnapshotAuthority(
            link, ledger=ledger, authority_private_key=key
        )
