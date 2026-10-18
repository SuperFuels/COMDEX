from __future__ import annotations

import base64
import json
import os

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.photon_offline_lease import (
    LEASE_SCHEMA,
    PhotonOfflineLeaseError,
    PhotonOfflineLeaseWallet,
    issue_offline_lease,
    verify_offline_lease,
)


def lease(authority):
    return issue_offline_lease(
        {
            "schema_version": LEASE_SCHEMA, "lease_id": "lease-1", "tenant_id": "tenant-1",
            "node_id": "node-1", "sequence": 1, "photon_limit": 100,
            "valid_from": "2026-10-17T00:00:00+00:00", "valid_until": "2026-10-18T00:00:00+00:00",
            "price_book_version": "price-1",
        },
        authority_private_key=authority,
    )


def wallet(tmp_path):
    authority = Ed25519PrivateKey.generate()
    service = PhotonOfflineLeaseWallet(
        tmp_path / "wallet.sqlite3", lease=lease(authority), authority_public_key=authority.public_key(),
        tenant_id="tenant-1", node_id="node-1", now="2026-10-17T01:00:00+00:00",
    )
    return authority, service


def test_successful_outcome_consumes_bounded_offline_photons(tmp_path):
    _, service = wallet(tmp_path)
    result = service.capture_success(
        receipt_id="receipt-1", action_type="invoice-created", photons=40,
        success_evidence_code="invoice-persisted", completed_at="2026-10-17T01:01:00+00:00",
        now="2026-10-17T01:01:00+00:00",
    )
    assert result["photons_used"] == 40
    assert result["photons_remaining"] == 60
    assert result["content_free"] is True


def test_replay_is_exact_and_collision_is_rejected(tmp_path):
    _, service = wallet(tmp_path)
    kwargs = dict(
        receipt_id="receipt-1", action_type="invoice-created", photons=40,
        success_evidence_code="invoice-persisted", completed_at="2026-10-17T01:01:00+00:00",
        now="2026-10-17T01:01:00+00:00",
    )
    service.capture_success(**kwargs)
    assert service.capture_success(**kwargs)["idempotent_replay"] is True
    with pytest.raises(PhotonOfflineLeaseError, match="collision"):
        service.capture_success(**{**kwargs, "photons": 41})


def test_lease_cannot_be_overspent_or_used_after_expiry(tmp_path):
    _, service = wallet(tmp_path)
    service.capture_success(
        receipt_id="receipt-1", action_type="invoice-created", photons=90,
        success_evidence_code="invoice-persisted", completed_at="2026-10-17T01:01:00+00:00",
        now="2026-10-17T01:01:00+00:00",
    )
    with pytest.raises(PhotonOfflineLeaseError, match="exhausted"):
        service.capture_success(
            receipt_id="receipt-2", action_type="quote-created", photons=11,
            success_evidence_code="quote-persisted", completed_at="2026-10-17T01:02:00+00:00",
            now="2026-10-17T01:02:00+00:00",
        )
    with pytest.raises(PhotonOfflineLeaseError, match="not_current"):
        service.capture_success(
            receipt_id="receipt-3", action_type="quote-created", photons=1,
            success_evidence_code="quote-persisted", completed_at="2026-10-18T01:02:00+00:00",
            now="2026-10-18T01:02:00+00:00",
        )


def test_tampered_or_wrong_node_lease_is_rejected(tmp_path):
    authority = Ed25519PrivateKey.generate()
    envelope = lease(authority)
    envelope["payload"]["photon_limit"] = 1000
    with pytest.raises(PhotonOfflineLeaseError, match="signature_invalid"):
        PhotonOfflineLeaseWallet(
            tmp_path / "wallet.sqlite3", lease=envelope, authority_public_key=authority.public_key(),
            tenant_id="tenant-1", node_id="node-1", now="2026-10-17T01:00:00+00:00",
        )
    with pytest.raises(PhotonOfflineLeaseError, match="identity_mismatch"):
        PhotonOfflineLeaseWallet(
            tmp_path / "wallet2.sqlite3", lease=lease(authority), authority_public_key=authority.public_key(),
            tenant_id="tenant-1", node_id="node-2", now="2026-10-17T01:00:00+00:00",
        )


def test_verifier_independently_enforces_lease_bounds(tmp_path):
    authority = Ed25519PrivateKey.generate()
    envelope = lease(authority)
    envelope["payload"]["photon_limit"] = 1_000_000_001
    canonical = json.dumps(
        envelope["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    envelope["signature"] = base64.urlsafe_b64encode(
        authority.sign(canonical)
    ).decode("ascii").rstrip("=")
    with pytest.raises(PhotonOfflineLeaseError, match="limit_invalid"):
        verify_offline_lease(
            envelope,
            authority_public_key=authority.public_key(),
            now="2026-10-17T01:00:00+00:00",
            expected_tenant_id="tenant-1",
            expected_node_id="node-1",
        )


def test_offline_wallet_store_is_private_and_refuses_symlink(tmp_path):
    authority, service = wallet(tmp_path)
    assert os.stat(service.database.parent).st_mode & 0o777 == 0o700
    assert os.stat(service.database).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-wallet.sqlite3"
    link.symlink_to(service.database)
    with pytest.raises(PhotonOfflineLeaseError, match="symlink_database_forbidden"):
        PhotonOfflineLeaseWallet(
            link,
            lease=lease(authority),
            authority_public_key=authority.public_key(),
            tenant_id="tenant-1",
            node_id="node-1",
            now="2026-10-17T01:00:00+00:00",
        )
