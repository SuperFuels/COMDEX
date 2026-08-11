from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import organization_authority_api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService


def _client(tmp_path, monkeypatch):
    repository = BusinessContainerRepository(tmp_path / "containers")
    service = OrganizationAuthorityService(repository)
    monkeypatch.setattr(organization_authority_api, "OrganizationAuthorityService", lambda: service)
    app = FastAPI()
    app.include_router(organization_authority_api.router)
    return TestClient(app)


def test_templates_support_manual_micro_business_setup(tmp_path, monkeypatch):
    payload = _client(tmp_path, monkeypatch).get("/api/aion/business/organisation/templates").json()
    assert payload["ok"] is True
    assert {item["id"] for item in payload["employment_types"]} >= {"owner", "employee", "self_employed", "contractor"}
    assert any(role["id"] == "role.owner_director" for role in payload["role_templates"])


def test_save_and_access_decision_round_trip(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    model = client.get("/api/aion/business/organisation/home-fixed").json()["model"]
    model["people"] = [{
        "id": "person.kevin", "name": "Kevin", "email": "kevin@example.com",
        "employment_type": "owner", "position_title": "Founder", "status": "active",
        "department_ids": [], "role_ids": ["role.owner_director"],
    }]
    response = client.put("/api/aion/business/organisation/home-fixed", json={
        "model": model, "expected_revision": 0, "changed_by": "test",
    })
    assert response.status_code == 200
    saved = response.json()["model"]
    assert saved["model_status"] == "authority_ready"
    decision = client.post(
        "/api/aion/business/organisation/home-fixed/access-decision",
        json={"person_id": "person.kevin", "capability": "boardroom.view_full"},
    ).json()["decision"]
    assert decision["allowed"] is True
    projection = client.get(
        "/api/aion/business/organisation/home-fixed/viewer-projection/person.kevin"
    ).json()["projection"]
    assert "finance" in projection["boardroom_sections"]


def test_stale_revision_is_rejected(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    model = client.get("/api/aion/business/organisation/home-fixed").json()["model"]
    model["people"] = [{"name": "Owner", "employment_type": "owner", "role_ids": ["role.owner_director"]}]
    assert client.put("/api/aion/business/organisation/home-fixed", json={"model": model, "expected_revision": 0}).status_code == 200
    conflict = client.put("/api/aion/business/organisation/home-fixed", json={"model": model, "expected_revision": 0})
    assert conflict.status_code == 409


def test_hr_workspace_is_loaded_after_the_application_bundle():
    index = open("desktop/mac/src/index.html", encoding="utf-8").read()
    source = open("desktop/mac/src/aion_hr_people_workspace.js", encoding="utf-8").read()
    assert index.index("app.js") < index.index("aion_hr_people_workspace.js")
    assert "data-aion-hr-workspace" in source
    assert "+ Add me as owner" in source
    assert "New self-employed person" in source
    assert "data-hrw-access-form" in source
