from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import commercial_adoption_api


def client(tmp_path, monkeypatch):
    monkeypatch.setattr(commercial_adoption_api, "service", lambda: commercial_adoption_api.CommercialAdoptionService(tmp_path))
    app = FastAPI(); app.include_router(commercial_adoption_api.router)
    return TestClient(app)


def test_dashboard_and_trial_controls_are_customer_visible_without_private_content(tmp_path, monkeypatch):
    browser = client(tmp_path, monkeypatch)
    empty = browser.get("/api/aion/business/commercial/tenant.acme")
    assert empty.status_code == 200
    assert empty.json()["private_content_included"] is False
    created = browser.post("/api/aion/business/commercial/trials/start", json={
        "tenant_id": "tenant.acme", "department": "sales", "actor_id": "owner.1",
        "days": 30, "action_limit": 100, "managed_cost_limit": 10, "currency": "EUR",
        "offer_version": "sales-2026-09", "consent_ref": "consent.1"
    })
    assert created.status_code == 200
    dashboard = browser.get("/api/aion/business/commercial/tenant.acme").json()
    assert dashboard["trials"][0]["department"] == "sales"
    assert "consent_receipt_hash" not in dashboard["trials"][0]
    cancelled = browser.post(f"/api/aion/business/commercial/trials/{created.json()['trial_id']}/cancel", json={
        "tenant_id": "tenant.acme", "actor_id": "owner.1", "cancellation_ref": "cancel.1"
    })
    assert cancelled.json()["state"] == "cancelled"


def test_capacity_overage_requires_exact_separate_approval(tmp_path, monkeypatch):
    browser = client(tmp_path, monkeypatch)
    denied = browser.post("/api/aion/business/commercial/capacity", json={
        "tenant_id": "tenant.acme", "department": "sales", "actor_id": "owner.1",
        "monthly_action_limit": 1000, "overage_allowed": True
    })
    assert denied.status_code == 400
    accepted = browser.post("/api/aion/business/commercial/capacity", json={
        "tenant_id": "tenant.acme", "department": "sales", "actor_id": "owner.1",
        "monthly_action_limit": 1000, "overage_allowed": True,
        "overage_approval_ref": "approval.1"
    })
    assert accepted.status_code == 200
