from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api.photon_control_plane_api import (
    create_photon_control_plane_router,
)
from backend.modules.aion_business.runtime.photon_billing_contracts import PhotonLedgerEntry
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    PhotonControlPlaneService,
    encode_control_plane_bearer,
    issue_control_plane_token,
)
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import PhotonRevolutFulfilment
from backend.modules.aion_business.runtime.photon_wallet_snapshot import PhotonWalletSnapshotAuthority


NOW = "2026-10-17T21:00:00Z"


def setup(tmp_path, scopes=("wallet.read", "activity.read", "billing.read", "checkout.create")):
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
    service = PhotonControlPlaneService(
        tmp_path / "access.sqlite3", ledger=ledger,
        wallet_snapshots=PhotonWalletSnapshotAuthority(
            tmp_path / "snapshots.sqlite3", ledger=ledger, authority_private_key=key
        ),
        revolut=PhotonRevolutFulfilment(tmp_path / "revolut.sqlite3", ledger=ledger),
    )
    app = FastAPI()
    app.include_router(
        create_photon_control_plane_router(
            service=service, authority_public_key=key.public_key(), clock=lambda: NOW
        )
    )
    envelope = issue_control_plane_token(
        token_id="token-1", subject_id="founder-1", tenant_id="tenant-1",
        scopes=scopes, issued_at="2026-10-17T20:30:00Z",
        expires_at="2026-10-17T21:30:00Z", authority_private_key=key,
    )
    return (
        TestClient(app),
        {"Authorization": "Bearer " + encode_control_plane_bearer(envelope)},
        service,
    )


def _fulfil_checkout(client, headers, service):
    checkout = client.post(
        "/api/control-plane/photon/checkout-intents", headers=headers,
        json={
            "request_id": "request-checkout-paid", "order_id": "order-paid",
            "external_reference": "reference-paid", "product_id": "bundle-100",
            "photons": 100, "amount_minor": 1000, "currency": "GBP",
            "price_book_version": "v1",
        },
    )
    assert checkout.status_code == 200

    class Verifier:
        def verify(self, raw_body, request_headers):
            return True

    class Orders:
        def retrieve_order(self, order_id):
            return {
                "id": order_id, "external_reference": "reference-paid",
                "amount_minor": 1000, "currency": "GBP", "state": "completed",
                "capture_mode": "automatic", "updated_at": NOW,
            }

    service.revolut.handle_webhook(
        b'{"event":"ORDER_COMPLETED","order_id":"order-paid"}', {},
        verifier=Verifier(), orders=Orders(),
    )


def test_authenticated_wallet_activity_and_checkout_routes_are_tenant_bound(tmp_path):
    client, headers, _ = setup(tmp_path)
    wallet = client.post(
        "/api/control-plane/photon/wallet-snapshot", headers=headers,
        json={"request_id": "request-wallet", "valid_until": "2026-10-17T21:15:00Z"},
    )
    activity = client.post(
        "/api/control-plane/photon/activity", headers=headers,
        json={"request_id": "request-activity", "limit": 20},
    )
    checkout = client.post(
        "/api/control-plane/photon/checkout-intents", headers=headers,
        json={
            "request_id": "request-checkout", "order_id": "order-1",
            "external_reference": "reference-1", "product_id": "bundle-100",
            "photons": 100, "amount_minor": 1000, "currency": "GBP",
            "price_book_version": "v1",
        },
    )
    commercial = client.post(
        "/api/control-plane/photon/commercial-status", headers=headers,
        json={"request_id": "request-commercial-status"},
    )
    assert wallet.status_code == 200 and wallet.json()["payload"]["tenant_id"] == "tenant-1"
    assert activity.status_code == 200 and activity.json()["items"][0]["source_receipt_id"] == "purchase-1"
    assert checkout.status_code == 200 and checkout.json()["tenant_id"] == "tenant-1"
    assert commercial.status_code == 200
    assert commercial.json()["tenant_id"] == "tenant-1"
    assert commercial.json()["commercial_hold"] is False


def test_missing_tampered_or_under_scoped_bearer_is_rejected(tmp_path):
    client, headers, _ = setup(tmp_path, scopes=("wallet.read",))
    assert client.post(
        "/api/control-plane/photon/activity",
        json={"request_id": "request-missing", "limit": 20},
    ).status_code == 401
    tampered = {"Authorization": headers["Authorization"] + "x"}
    assert client.post(
        "/api/control-plane/photon/activity", headers=tampered,
        json={"request_id": "request-tampered", "limit": 20},
    ).status_code == 401
    denied = client.post(
        "/api/control-plane/photon/activity", headers=headers,
        json={"request_id": "request-denied", "limit": 20},
    )
    assert denied.status_code == 403


def test_caller_cannot_inject_tenant_id_into_checkout_request(tmp_path):
    client, headers, _ = setup(tmp_path)
    response = client.post(
        "/api/control-plane/photon/checkout-intents", headers=headers,
        json={
            "request_id": "request-checkout", "tenant_id": "tenant-2",
            "order_id": "order-1", "external_reference": "reference-1",
            "product_id": "bundle-100", "photons": 100, "amount_minor": 1000,
            "currency": "GBP", "price_book_version": "v1",
        },
    )
    assert response.status_code == 422


def test_billing_records_are_tenant_bound_content_free_and_exportable(tmp_path):
    client, headers, service = setup(tmp_path)
    _fulfil_checkout(client, headers, service)
    response = client.post(
        "/api/control-plane/photon/billing-records", headers=headers,
        json={"request_id": "request-records", "limit": 20, "export_format": "json"},
    )
    assert response.status_code == 200
    record = response.json()["items"][0]
    assert record["receipt_id"] == "revolut:order-paid"
    assert record["tax_invoice"] is False
    assert record["customer_content_included"] is False
    assert record["local_model_tokens_billed"] is False
    assert "tenant_id" not in record
    assert not ({"prompt", "message", "document", "file_path"} & set(record))

    csv_response = client.post(
        "/api/control-plane/photon/billing-records", headers=headers,
        json={"request_id": "request-records-csv", "limit": 20, "export_format": "csv"},
    )
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "revolut:order-paid" in csv_response.text
