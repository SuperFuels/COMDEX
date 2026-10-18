from __future__ import annotations

import os
import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api.photon_pricing_admin_api import (
    create_photon_pricing_admin_router,
)
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    encode_control_plane_bearer,
    issue_control_plane_token,
)
from backend.modules.aion_business.runtime.photon_price_book_store import (
    PhotonPriceBookStore,
)
from backend.modules.aion_business.runtime.photon_pricing_admin import (
    PhotonPricingAdminAudit,
)
from backend.modules.aion_fabric.identity import DeviceIdentity


NOW = "2026-10-17T20:30:00+00:00"


def _payload(*, request_id: str, price: int = 1) -> dict:
    return {
        "request_id": request_id,
        "version": "gb-founder-v1",
        "currency": "GBP",
        "minor_units_per_1000_photons": price,
        "action_rates": {
            "quote.prepared": 25,
            "invoice.reconciled": 40,
        },
        "effective_at": "2026-11-01T00:00:00+00:00",
        "region": "GB",
        "cohort": "all",
        "reason": "Founder market-making calibration",
    }


def _setup(tmp_path):
    admin_key = Ed25519PrivateKey.generate()
    customer_key = Ed25519PrivateKey.generate()
    signing_key = Ed25519PrivateKey.generate()
    store = PhotonPriceBookStore(tmp_path / "price-books.sqlite3")
    audit = PhotonPricingAdminAudit(tmp_path / "pricing-audit.sqlite3")
    app = FastAPI()
    app.include_router(
        create_photon_pricing_admin_router(
            store=store,
            audit=audit,
            admin_authority_public_key=admin_key.public_key(),
            price_book_signer=DeviceIdentity(signing_key),
            platform_tenant_id="tessaris-platform",
            reauthentication_verifier=lambda actor, evidence, at: (
                actor.subject_id == "founder-1"
                and evidence == "recent-webauthn-assertion"
                and at == NOW
            ),
            clock=lambda: NOW,
        )
    )

    def headers(key, *, tenant="tessaris-platform", scopes=("pricing.manage",)):
        token = issue_control_plane_token(
            token_id=f"token-{tenant}",
            subject_id="founder-1",
            tenant_id=tenant,
            scopes=scopes,
            issued_at="2026-10-17T20:00:00+00:00",
            expires_at="2026-10-17T21:00:00+00:00",
            authority_private_key=key,
        )
        return {"Authorization": "Bearer " + encode_control_plane_bearer(token)}

    return TestClient(app), headers(admin_key), headers(customer_key), store, audit


def test_founder_can_preview_then_reauthenticate_and_publish(tmp_path):
    client, admin_headers, _, store, audit = _setup(tmp_path)
    preview = client.post(
        "/api/control-plane/photon/admin/pricing/preview",
        headers=admin_headers,
        json=_payload(request_id="preview-1", price=1),
    )
    assert preview.status_code == 200
    assert preview.json()["minor_units_per_1000_photons"] == 1
    assert preview.json()["published"] is False

    publish_payload = {
        **_payload(request_id="publish-1", price=1),
        "approved_preview_hash": preview.json()["price_book_hash"],
        "confirmation": "PUBLISH PHOTON PRICE BOOK",
        "reauthentication_evidence_id": "recent-webauthn-assertion",
    }
    published = client.post(
        "/api/control-plane/photon/admin/pricing/publish",
        headers=admin_headers,
        json=publish_payload,
    )
    assert published.status_code == 200
    assert published.json()["payload"]["minor_units_per_1000_photons"] == 1
    assert store.get("gb-founder-v1")["preview_hash"] == preview.json()["price_book_hash"]

    history = client.post(
        "/api/control-plane/photon/admin/pricing/history",
        headers=admin_headers,
        json={"request_id": "history-1", "limit": 10},
    )
    assert history.status_code == 200
    assert [item["version"] for item in history.json()["items"]] == ["gb-founder-v1"]
    with sqlite3.connect(audit.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM photon_pricing_admin_audit"
        ).fetchone()[0] == 3


def test_pricing_admin_audit_store_is_private_and_refuses_symlink(tmp_path):
    store = PhotonPricingAdminAudit(tmp_path / "private" / "pricing-audit.sqlite3")
    assert os.stat(store.path.parent).st_mode & 0o777 == 0o700
    assert os.stat(store.path).st_mode & 0o777 == 0o600
    link = tmp_path / "linked-pricing-audit.sqlite3"
    link.symlink_to(store.path)
    with pytest.raises(ValueError, match="symlink_database_forbidden"):
        PhotonPricingAdminAudit(link)


def test_customer_key_wrong_tenant_and_missing_reauthentication_fail_closed(tmp_path):
    client, admin_headers, customer_headers, _, audit = _setup(tmp_path)
    assert client.post(
        "/api/control-plane/photon/admin/pricing/preview",
        headers=customer_headers,
        json=_payload(request_id="customer-preview"),
    ).status_code == 401

    preview = client.post(
        "/api/control-plane/photon/admin/pricing/preview",
        headers=admin_headers,
        json=_payload(request_id="preview-2"),
    ).json()
    denied = client.post(
        "/api/control-plane/photon/admin/pricing/publish",
        headers=admin_headers,
        json={
            **_payload(request_id="publish-denied"),
            "approved_preview_hash": preview["price_book_hash"],
            "confirmation": "PUBLISH PHOTON PRICE BOOK",
            "reauthentication_evidence_id": "not-current",
        },
    )
    assert denied.status_code == 403
    assert "reauthentication_required" in denied.text
    with sqlite3.connect(audit.path) as connection:
        outcome = connection.execute(
            "SELECT outcome FROM photon_pricing_admin_audit WHERE request_id = ?",
            ("publish-denied",),
        ).fetchone()[0]
    assert outcome == "reauthentication_denied"


def test_publish_cannot_change_approved_slider_value(tmp_path):
    client, admin_headers, _, store, _ = _setup(tmp_path)
    preview = client.post(
        "/api/control-plane/photon/admin/pricing/preview",
        headers=admin_headers,
        json=_payload(request_id="preview-3", price=1),
    ).json()
    response = client.post(
        "/api/control-plane/photon/admin/pricing/publish",
        headers=admin_headers,
        json={
            **_payload(request_id="publish-mismatch", price=3),
            "approved_preview_hash": preview["price_book_hash"],
            "confirmation": "PUBLISH PHOTON PRICE BOOK",
            "reauthentication_evidence_id": "recent-webauthn-assertion",
        },
    )
    assert response.status_code == 403
    assert "preview_mismatch" in response.text
    assert store.list() == []


def test_founder_can_inspect_and_cancel_only_a_future_price_book(tmp_path):
    client, admin_headers, _, store, audit = _setup(tmp_path)
    preview = client.post(
        "/api/control-plane/photon/admin/pricing/preview",
        headers=admin_headers,
        json=_payload(request_id="preview-cancel"),
    ).json()
    published = client.post(
        "/api/control-plane/photon/admin/pricing/publish",
        headers=admin_headers,
        json={
            **_payload(request_id="publish-cancel"),
            "approved_preview_hash": preview["price_book_hash"],
            "confirmation": "PUBLISH PHOTON PRICE BOOK",
            "reauthentication_evidence_id": "recent-webauthn-assertion",
        },
    )
    assert published.status_code == 200

    before = client.post(
        "/api/control-plane/photon/admin/pricing/current",
        headers=admin_headers,
        json={
            "request_id": "current-before-cancel",
            "currency": "GBP",
            "region": "GB",
            "cohort": "all",
            "as_of": NOW,
        },
    )
    assert before.status_code == 200
    assert before.json()["active"] is None
    assert [item["version"] for item in before.json()["scheduled"]] == ["gb-founder-v1"]

    cancelled = client.post(
        "/api/control-plane/photon/admin/pricing/cancel",
        headers=admin_headers,
        json={
            "request_id": "cancel-1",
            "version": "gb-founder-v1",
            "reason": "Founder withdrew the scheduled calibration",
            "confirmation": "CANCEL PHOTON PRICE BOOK",
            "reauthentication_evidence_id": "recent-webauthn-assertion",
        },
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["version"] == "gb-founder-v1"
    assert store.get("gb-founder-v1")["version"] == "gb-founder-v1"

    after = client.post(
        "/api/control-plane/photon/admin/pricing/current",
        headers=admin_headers,
        json={
            "request_id": "current-after-cancel",
            "currency": "GBP",
            "region": "GB",
            "cohort": "all",
            "as_of": NOW,
        },
    )
    assert after.status_code == 200
    assert after.json()["scheduled"] == []
    history = client.post(
        "/api/control-plane/photon/admin/pricing/history",
        headers=admin_headers,
        json={"request_id": "history-after-cancel", "limit": 10},
    ).json()
    assert history["cancellations"][0]["version"] == "gb-founder-v1"
    with sqlite3.connect(audit.path) as connection:
        actions = {
            row[0] for row in connection.execute(
                "SELECT action FROM photon_pricing_admin_audit"
            ).fetchall()
        }
    assert {"pricing.current", "pricing.cancel"}.issubset(actions)


def test_active_price_book_cannot_be_cancelled(tmp_path):
    client, admin_headers, _, store, _ = _setup(tmp_path)
    preview = client.post(
        "/api/control-plane/photon/admin/pricing/preview",
        headers=admin_headers,
        json=_payload(request_id="preview-active"),
    ).json()
    client.post(
        "/api/control-plane/photon/admin/pricing/publish",
        headers=admin_headers,
        json={
            **_payload(request_id="publish-active"),
            "approved_preview_hash": preview["price_book_hash"],
            "confirmation": "PUBLISH PHOTON PRICE BOOK",
            "reauthentication_evidence_id": "recent-webauthn-assertion",
        },
    )
    with pytest.raises(ValueError, match="active_photon_price_book_cannot_be_cancelled"):
        store.cancel(
            "gb-founder-v1",
            actor_id="founder-1",
            cancelled_at="2026-11-02T00:00:00+00:00",
            reason="Too late",
            reauthenticated=True,
            confirmation="CANCEL PHOTON PRICE BOOK",
        )
