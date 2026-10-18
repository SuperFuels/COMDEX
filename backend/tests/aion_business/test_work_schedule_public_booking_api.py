from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import work_schedule_api as api


class _Sales:
    calls: list[dict] = []

    def ingest_website_enquiry(self, workspace_id, endpoint_id, **kwargs):
        self.calls.append({"workspace_id": workspace_id, "endpoint_id": endpoint_id, **kwargs})
        if kwargs["token"] != "one-time-secret":
            raise PermissionError("website_intake_token_invalid")
        return {
            "contact": {
                "contact_id": "contact-canonical-pat", "name": "Pat Prospect",
                "email": "pat@example.test", "phone": "+34600111222",
                "address": "4 Billing Road",
            },
            "opportunity": {
                "opportunity_id": "opportunity-pat", "source_reference": "endpoint-1:form-1",
            },
        }


class _Schedule:
    calls: list[dict] = []

    def create_intake(self, workspace_id, fields, *, channel):
        self.calls.append({"workspace_id": workspace_id, "fields": dict(fields), "channel": channel})
        return {"intake": [{"id": "intake-1", "state": fields.get("state"), **dict(fields)}]}


def _client(monkeypatch):
    _Sales.calls.clear()
    _Schedule.calls.clear()
    monkeypatch.setattr(api, "SalesRevenueService", _Sales)
    monkeypatch.setattr(api, "WorkScheduleService", _Schedule)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_secured_public_booking_links_sales_contact_and_schedule_intake(monkeypatch):
    client = _client(monkeypatch)
    response = client.post(
        "/api/aion/business/work-schedule/public/acme/booking",
        headers={"X-Tessaris-Intake-Key": "one-time-secret"},
        json={
            "sales_endpoint_id": "endpoint-1", "channel": "website",
            "fields": {
                "event_id": "form-1", "title": "Boiler service", "customer": "Pat Prospect",
                "customer_email": "pat@example.test", "message": "Please book a service",
                "customer_address": "4 Billing Road",
                "state": "Ready to schedule",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["customer_id"] == "contact-canonical-pat"
    assert response.json()["sales_opportunity_id"] == "opportunity-pat"
    assert _Sales.calls[0]["payload"]["enquiry"] == "Please book a service"
    assert _Sales.calls[0]["payload"]["address"] == "4 Billing Road"
    assert _Schedule.calls[0]["fields"]["source_reference"] == "endpoint-1:form-1"
    assert _Schedule.calls[0]["fields"]["customer_address"] == "4 Billing Road"


def test_sales_linkage_requires_the_secured_intake_token(monkeypatch):
    client = _client(monkeypatch)
    response = client.post(
        "/api/aion/business/work-schedule/public/acme/booking",
        json={
            "sales_endpoint_id": "endpoint-1",
            "fields": {"event_id": "form-1", "customer": "Pat", "message": "Book me"},
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "website_intake_token_required"
    assert _Schedule.calls == []
