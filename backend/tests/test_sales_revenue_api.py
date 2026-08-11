from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import sales_revenue_api as api
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService
from backend.tests.test_finance_bookkeeping_service import configure


def client(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    monkeypatch.setattr(api, "sales", SalesRevenueService(repository, authority))
    app = FastAPI(); app.include_router(api.router)
    return TestClient(app)


def test_sales_api_exposes_provider_neutral_vertical_without_external_side_effects(monkeypatch, tmp_path):
    http = client(monkeypatch, tmp_path)
    catalog = http.get("/api/aion/sales/acme")
    assert catalog.status_code == 200
    assert catalog.json()["connector_boundary"]["external_writes_enabled"] is False
    created = http.post("/api/aion/sales/acme/enquiries", json={
        "name": "Web Lead", "email": "lead@example.test", "enquiry": "Need a quote",
        "source": "website", "source_reference": "form-1", "attribution": {"utm_source": "google"},
        "consent": {}, "created_by_person_id": "person.owner",
    })
    assert created.status_code == 200
    payload = created.json()
    assert payload["external_action_performed"] is False
    assert payload["opportunity"]["stage"] == "new"


def test_sales_api_denies_voice_session_without_ai_disclosure(monkeypatch, tmp_path):
    http = client(monkeypatch, tmp_path)
    created = http.post("/api/aion/sales/acme/enquiries", json={
        "name": "Call Lead", "phone": "+34600111222", "enquiry": "Call me",
        "source": "inbound_call", "created_by_person_id": "person.owner",
    }).json()
    response = http.post(
        f"/api/aion/sales/acme/opportunities/{created['opportunity']['opportunity_id']}/sessions",
        json={"channel": "telephone", "provider": "retell", "ai_disclosure": False,
              "recording_consent": "not_recorded", "started_by_person_id": "person.owner"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "ai_identity_disclosure_required"


def test_sales_api_accepts_only_authenticated_idempotent_public_form_events(monkeypatch, tmp_path):
    http = client(monkeypatch, tmp_path)
    endpoint = http.post("/api/aion/sales/acme/intake-endpoints", json={
        "name": "Quote form", "created_by_person_id": "person.owner"}).json()["endpoint"]
    payload = {"event_id": "form-1", "name": "Taylor", "email": "taylor@example.test",
               "enquiry": "Need a quote", "utm_source": "google"}
    denied = http.post(f"/api/aion/sales/public-intake/acme/{endpoint['endpoint_id']}", json=payload)
    assert denied.status_code == 403
    accepted = http.post(f"/api/aion/sales/public-intake/acme/{endpoint['endpoint_id']}", json=payload,
                         headers={"X-Tessaris-Intake-Key": endpoint["token"]})
    assert accepted.status_code == 200
    assert accepted.json()["opportunity"]["attribution"]["utm_source"] == "google"


def test_sales_api_runs_and_promotes_exact_simulated_agent_version(monkeypatch, tmp_path):
    http = client(monkeypatch, tmp_path)
    simulated = http.post("/api/aion/sales/acme/playbooks/inbound-enquiry/simulations",
                          json={"run_by_person_id": "person.owner"}).json()
    assert simulated["run"]["passed"] == 11
    promoted = http.post("/api/aion/sales/acme/playbooks/inbound-enquiry/promote", json={
        "expected_playbook_hash": simulated["playbook"]["playbook_hash"],
        "promoted_by_person_id": "person.owner"})
    assert promoted.status_code == 200
    assert promoted.json()["playbook"]["status"] == "promoted_for_controlled_use"
