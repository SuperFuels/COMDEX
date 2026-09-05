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


def test_sales_api_accepts_a_structured_business_contact(monkeypatch, tmp_path):
    http = client(monkeypatch, tmp_path)
    created = http.post("/api/aion/sales/acme/enquiries", json={
        "customer_type": "business", "name": "Alex Morgan",
        "first_name": "Alex", "last_name": "Morgan", "email": "alex@buyer.test",
        "company_name": "Buyer Limited", "position_title": "Finance Director",
        "department": "Finance", "phone_extension": "51",
        "address": "20 Commerce Road", "enquiry": "Need an annual proposal",
        "source": "manual", "created_by_person_id": "person.owner",
    })
    assert created.status_code == 200
    contact = created.json()["contact"]
    assert contact["customer_type"] == "business"
    assert contact["company_name"] == "Buyer Limited"
    assert contact["department"] == "Finance"
    assert contact["phone_extension"] == "51"


def test_sales_api_exposes_one_receipted_customer_job_feed(monkeypatch, tmp_path):
    http = client(monkeypatch, tmp_path)
    created = http.post("/api/aion/sales/acme/enquiries", json={
        "name": "Roofing Customer", "email": "roof@example.test",
        "enquiry": "Survey and quote a leaking roof", "source": "inbound_email",
        "created_by_person_id": "person.owner",
    }).json()
    opportunity_id = created["opportunity"]["opportunity_id"]

    update = http.post(f"/api/aion/sales/acme/opportunities/{opportunity_id}/work-feed/events", json={
        "kind": "voice_instruction", "title": "Survey scope dictated from site",
        "summary": "Repair flashing and replace damaged tiles; prepare a VAT-inclusive quote.",
        "details": {"materials": "Tiles and flashing", "labour_days": 2},
        "lifecycle_stage": "survey", "source": "pilot", "provider": "tessaris",
        "source_reference": "voice-session-17", "attachments": [{
            "name": "roof-photo.jpg", "media_type": "image/jpeg",
            "sha256": "b" * 64, "size_bytes": 4096,
            "source_reference": "file-cabinet/roof-photo.jpg",
        }],
        "action": {"status": "recorded", "external_action_performed": False},
        "recorded_by_person_id": "person.owner",
    })
    assert update.status_code == 200
    assert update.json()["event"]["kind"] == "voice_instruction"
    assert update.json()["work_feed"]["current_stage"] == "survey"

    feed = http.get(f"/api/aion/sales/acme/opportunities/{opportunity_id}/work-feed")
    assert feed.status_code == 200
    assert [event["kind"] for event in feed.json()["work_feed"]["events"]] == [
        "enquiry_received", "voice_instruction",
    ]

    uploaded = http.post(
        f"/api/aion/sales/acme/opportunities/{opportunity_id}/work-feed/attachments",
        data={"recorded_by_person_id": "person.owner"},
        files={"file": ("site-photo.png", b"\x89PNG\r\n\x1a\ncustomer-evidence", "image/png")},
    )
    assert uploaded.status_code == 200
    attachment = uploaded.json()["attachment"]
    assert attachment["media_type"] == "image/png"
    assert attachment["source_reference"].endswith(attachment["attachment_id"])

    read_back = http.get(attachment["source_reference"])
    assert read_back.status_code == 200
    assert read_back.content == b"\x89PNG\r\n\x1a\ncustomer-evidence"


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


def test_sales_api_exposes_versioned_call_centre_agent_lifecycle(monkeypatch, tmp_path):
    http = client(monkeypatch, tmp_path)
    created = http.post("/api/aion/sales/acme/call-centre/agents", json={
        "name": "Outbound qualification", "direction": "outbound",
        "created_by_person_id": "person.owner",
    })
    assert created.status_code == 200
    agent = created.json()["agent"]
    configured = http.put(
        f"/api/aion/sales/acme/call-centre/agents/{agent['agent_id']}", json={
            "expected_agent_hash": agent["agent_hash"],
            "configured_by_person_id": "person.owner",
            "setup": {
                "name": "Outbound qualification", "direction": "outbound",
                "phone_assignment": {"number": "+441234567899", "provider": "retell"},
                "knowledge": {"business_name": "Acme", "business_summary": "Approved services.",
                              "approved_offers": "Service assessment."},
                "objective": {"success_definition": "Qualify the customer for human review."},
            },
        })
    assert configured.status_code == 200
    tested = http.post(
        f"/api/aion/sales/acme/call-centre/agents/{agent['agent_id']}/test",
        json={"run_by_person_id": "person.owner"})
    assert tested.status_code == 200
    tested_agent = tested.json()["agent"]
    minted = http.post(
        f"/api/aion/sales/acme/call-centre/agents/{agent['agent_id']}/mint", json={
            "expected_agent_hash": tested_agent["agent_hash"],
            "minted_by_person_id": "person.owner",
        })
    assert minted.status_code == 200
    assert minted.json()["contract"]["contract_hash"].startswith("sha256:")
    listing = http.get("/api/aion/sales/acme/call-centre/agents")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["name"] == "Outbound qualification"
