from __future__ import annotations

import base64
import os
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedgerEntry,
    canonical_bytes,
)
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    PhotonControlPlaneAccessError,
    PhotonControlPlaneService,
    issue_control_plane_token,
    verify_control_plane_token,
)
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import PhotonRevolutFulfilment
from backend.modules.aion_business.runtime.photon_wallet_snapshot import PhotonWalletSnapshotAuthority


NOW = "2026-10-17T21:00:00Z"


def token(key, *, tenant="tenant-1", scopes=("wallet.read", "activity.read", "checkout.create")):
    return issue_control_plane_token(
        token_id=f"token-{tenant}", subject_id="founder-1", tenant_id=tenant,
        scopes=scopes, issued_at="2026-10-17T20:30:00Z",
        expires_at="2026-10-17T21:30:00Z", authority_private_key=key,
    )


def setup(tmp_path):
    ledger = PhotonLedgerStore(tmp_path / "ledger.sqlite3")
    for tenant, photons in (("tenant-1", 100), ("tenant-2", 900)):
        ledger.post(
            transaction_id=f"grant-{tenant}", tenant_id=tenant, reason="bundle_grant",
            source_receipt_id=f"purchase-{tenant}", rate_card_version="v1",
            idempotency_key=f"grant-{tenant}", recorded_at="2026-10-17T19:00:00Z",
            entries=[
                PhotonLedgerEntry("platform.grant-liability", -photons),
                PhotonLedgerEntry("customer.available", photons),
            ],
        )
    authority_key = Ed25519PrivateKey.generate()
    snapshots = PhotonWalletSnapshotAuthority(
        tmp_path / "snapshots.sqlite3", ledger=ledger,
        authority_private_key=authority_key,
    )
    revolut = PhotonRevolutFulfilment(tmp_path / "revolut.sqlite3", ledger=ledger)
    service = PhotonControlPlaneService(
        tmp_path / "access.sqlite3", ledger=ledger,
        wallet_snapshots=snapshots, revolut=revolut,
    )
    return authority_key, ledger, service


def test_signed_token_is_tenant_bound_current_and_tamper_evident(tmp_path):
    key, _, _ = setup(tmp_path)
    envelope = token(key)
    principal = verify_control_plane_token(
        envelope, authority_public_key=key.public_key(), now=NOW
    )
    assert principal.tenant_id == "tenant-1"
    envelope["payload"]["tenant_id"] = "tenant-2"
    with pytest.raises(PhotonControlPlaneAccessError, match="signature_invalid"):
        verify_control_plane_token(envelope, authority_public_key=key.public_key(), now=NOW)
    with pytest.raises(PhotonControlPlaneAccessError, match="not_current"):
        verify_control_plane_token(
            token(key), authority_public_key=key.public_key(), now="2026-10-17T22:00:00Z"
        )


def test_verifier_independently_enforces_maximum_token_lifetime(tmp_path):
    key, _, _ = setup(tmp_path)
    envelope = token(key)
    envelope["payload"]["expires_at"] = "2026-10-17T22:30:01Z"
    envelope["signature"] = base64.urlsafe_b64encode(
        key.sign(canonical_bytes(envelope["payload"]))
    ).decode("ascii").rstrip("=")
    with pytest.raises(PhotonControlPlaneAccessError, match="period_invalid"):
        verify_control_plane_token(
            envelope, authority_public_key=key.public_key(), now=NOW
        )


def test_wallet_and_activity_derive_tenant_from_verified_principal(tmp_path):
    key, _, service = setup(tmp_path)
    principal = verify_control_plane_token(
        token(key), authority_public_key=key.public_key(), now=NOW
    )
    wallet = service.wallet_snapshot(
        principal, request_id="request-wallet-1", issued_at=NOW,
        valid_until="2026-10-17T21:30:00Z",
    )
    activity = service.activity(
        principal, request_id="request-activity-1", limit=20, recorded_at=NOW
    )
    assert wallet["payload"]["tenant_id"] == "tenant-1"
    assert wallet["payload"]["available_photons"] == 100
    assert len(activity) == 1 and activity[0]["source_receipt_id"] == "purchase-tenant-1"
    assert "tenant-2" not in str(activity)


def test_checkout_tenant_is_never_accepted_from_request_body(tmp_path):
    key, _, service = setup(tmp_path)
    principal = verify_control_plane_token(
        token(key), authority_public_key=key.public_key(), now=NOW
    )
    intent = service.record_checkout_intent(
        principal, request_id="request-checkout-1", order_id="order-1",
        external_reference="reference-1", product_id="bundle-100", photons=100,
        amount_minor=1000, currency="GBP", price_book_version="v1", created_at=NOW,
    )
    assert intent["tenant_id"] == "tenant-1"


def test_missing_scope_is_denied_and_audited_without_customer_content(tmp_path):
    key, _, service = setup(tmp_path)
    principal = verify_control_plane_token(
        token(key, scopes=("wallet.read",)), authority_public_key=key.public_key(), now=NOW
    )
    with pytest.raises(PermissionError, match="scope_denied"):
        service.activity(
            principal, request_id="request-denied-1", limit=20, recorded_at=NOW
        )
    with sqlite3.connect(service.path) as connection:
        row = connection.execute(
            "SELECT action, outcome, customer_content_included FROM photon_control_plane_access_audit"
        ).fetchone()
    assert row == ("wallet.activity", "denied", 0)


def test_access_request_ids_are_immutable_and_collision_checked(tmp_path):
    key, _, service = setup(tmp_path)
    principal = verify_control_plane_token(
        token(key), authority_public_key=key.public_key(), now=NOW
    )
    service.activity(principal, request_id="request-1", limit=1, recorded_at=NOW)
    with pytest.raises(PhotonControlPlaneAccessError, match="request_replayed"):
        service.activity(principal, request_id="request-1", limit=1, recorded_at=NOW)
    with pytest.raises(PhotonControlPlaneAccessError, match="request_id_collision"):
        service.wallet_snapshot(
            principal, request_id="request-1", issued_at=NOW,
            valid_until="2026-10-17T21:30:00Z",
        )


def test_access_audit_store_is_private_and_refuses_symlink(tmp_path):
    _, _, service = setup(tmp_path)
    assert os.stat(service.path.parent).st_mode & 0o777 == 0o700
    assert os.stat(service.path).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-access.sqlite3"
    link.symlink_to(service.path)
    with pytest.raises(PhotonControlPlaneAccessError, match="symlink_database_forbidden"):
        PhotonControlPlaneService(
            link,
            ledger=service.ledger,
            wallet_snapshots=service.wallet_snapshots,
            revolut=service.revolut,
        )
