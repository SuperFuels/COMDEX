from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from backend.modules.aion_business.api import business_twin_data_api
from backend.modules.aion_business.runtime.business_connector_onboarding_service import (
    BusinessConnectorOnboardingService,
)


def _service(tmp_path, **overrides):
    defaults = {
        "business_root": tmp_path,
        "file_loader": lambda _business_id: {
            "folders": [
                {"id": "folder-1", "type": "folder", "children": [
                    {"id": "document-1", "type": "document", "created_by": "user"},
                    {"id": "receipt-1", "type": "business_container_artifact", "status": "verified"},
                ]},
            ],
        },
        "google_probe": lambda: {
            "provider": "google",
            "auth_status": "connected",
            "connector_health": "healthy",
            "token_present": True,
            "scopes": ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/calendar.events"],
        },
        "crm_probe": lambda: {
            "provider": "hubspot",
            "auth_status": "connected",
            "connector_health": "healthy",
        },
        "xero_probe": lambda _business_id: {
            "provider": "xero",
            "connected": True,
            "status": "connected",
            "last_sync_status": "verified",
            "sync_summary": {"invoice_count": 4},
        },
    }
    defaults.update(overrides)
    return BusinessConnectorOnboardingService(**defaults)


def test_unified_connector_snapshot_is_read_only_secret_free_and_projects_counts(tmp_path):
    opportunity_dir = tmp_path / "sample-company" / "sales" / "revenue_spine" / "opportunities"
    opportunity_dir.mkdir(parents=True)
    (opportunity_dir / "email.json").write_text(json.dumps({
        "source": "gmail", "stage": "new", "email": "private@example.test",
        "appointment": {"starts_at": "2026-09-10T09:00:00Z"},
    }), encoding="utf-8")
    (opportunity_dir / "crm.json").write_text(json.dumps({
        "source": "hubspot_crm", "stage": "qualified", "customer_name": "Private Customer",
    }), encoding="utf-8")

    snapshot = _service(tmp_path).snapshot("Sample Company")
    cards = {card["connector_id"]: card for card in snapshot["cards"]}

    assert snapshot["business_id"] == "sample-company"
    assert set(cards) == {"files", "gmail", "calendar", "crm_sales", "xero"}
    assert snapshot["connected_count"] == 5
    assert snapshot["external_write_performed"] is False
    assert all(value is False for value in snapshot["privacy"].values())
    assert cards["files"]["projection"]["summary"] == {"document_count": 2, "protected_record_count": 1}
    assert cards["gmail"]["projection"]["summary"]["imported_enquiry_count"] == 1
    assert cards["calendar"]["projection"]["summary"]["appointment_evidence_count"] == 1
    assert cards["crm_sales"]["projection"]["summary"]["crm_opportunity_count"] == 1
    assert cards["xero"]["connect"]["http_method"] == "POST"
    encoded = json.dumps(snapshot).lower()
    assert "private@example.test" not in encoded
    assert "private customer" not in encoded
    assert "password" not in encoded
    assert "access_token" not in encoded


def test_google_connection_requires_real_token_and_calendar_scope(tmp_path):
    snapshot = _service(
        tmp_path,
        google_probe=lambda: {"auth_status": "connected", "token_present": False, "scopes": []},
    ).snapshot("sample-company")
    cards = {card["connector_id"]: card for card in snapshot["cards"]}
    assert cards["gmail"]["connected"] is False
    assert cards["calendar"]["connected"] is False


def test_one_failed_provider_does_not_hide_other_connectors(tmp_path):
    def unavailable():
        raise RuntimeError("provider unavailable")

    snapshot = _service(tmp_path, crm_probe=unavailable).snapshot("sample-company")
    cards = {card["connector_id"]: card for card in snapshot["cards"]}
    assert len(cards) == 5
    assert cards["crm_sales"]["connected"] is False
    assert cards["crm_sales"]["status"] == "unavailable"
    assert cards["files"]["connected"] is True


def test_connector_onboarding_api_uses_unified_service(monkeypatch):
    expected = {"ok": True, "cards": [{"connector_id": "files"}]}

    class Stub:
        def snapshot(self, candidate):
            assert candidate == "sample-company"
            return expected

    monkeypatch.setattr(business_twin_data_api, "_connector_onboarding", lambda: Stub())
    assert business_twin_data_api.get_business_connector_onboarding("sample-company") == expected


def test_connector_onboarding_api_rejects_invalid_business_id(monkeypatch):
    class Stub:
        def snapshot(self, _candidate):
            raise ValueError("invalid business")

    monkeypatch.setattr(business_twin_data_api, "_connector_onboarding", lambda: Stub())
    with pytest.raises(HTTPException) as exc:
        business_twin_data_api.get_business_connector_onboarding("bad")
    assert exc.value.status_code == 400

