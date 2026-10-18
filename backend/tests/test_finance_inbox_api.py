from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import finance_inbox_api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_inbox_service import FinanceInboxService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _client(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", runtime)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", runtime / "business_containers")
    monkeypatch.setattr(AIONBusinessPaths, "AUDIT", runtime / "audit")
    repository = BusinessContainerRepository(runtime / "business_containers")
    authority = OrganizationAuthorityService(repository)
    model = authority.empty("acme")
    model["people"] = [
        {"id": "person.owner", "name": "Owner", "employment_type": "owner", "status": "active", "role_ids": ["role.owner_director"]},
        {"id": "person.worker", "name": "Worker", "employment_type": "employee", "status": "active", "manager_id": "person.owner", "role_ids": ["role.employee"]},
    ]
    authority.save("acme", model)
    service = FinanceInboxService(repository)
    monkeypatch.setattr(finance_inbox_api, "FinanceInboxService", lambda: service)
    app = FastAPI()
    app.include_router(finance_inbox_api.router)
    return TestClient(app)


def test_upload_review_approve_and_file_round_trip(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    upload = client.post(
        "/api/aion/business/finance-inbox/acme/documents",
        data={"document_type": "receipt", "submitted_by_person_id": "person.worker"},
        files={"file": ("receipt.jpg", b"image-bytes", "image/jpeg")},
    )
    assert upload.status_code == 200
    document_id = upload.json()["document"]["id"]
    assert client.get(f"/api/aion/business/finance-inbox/acme/documents/{document_id}/file").content == b"image-bytes"
    review = client.put(
        f"/api/aion/business/finance-inbox/acme/documents/{document_id}/review",
        json={
            "expected_revision": 1, "reviewed_by_person_id": "person.owner",
            "fields": {"supplier": "Cafe", "document_date": "2026-08-09", "total": 12.5, "tax": 1.14, "net": 11.36},
            "destination": "expense",
        },
    )
    assert review.status_code == 200
    assert review.json()["document"]["status"] == "awaiting_approval"
    approved = client.post(
        f"/api/aion/business/finance-inbox/acme/documents/{document_id}/decision",
        json={"decision": "approve", "decided_by_person_id": "person.owner", "expected_revision": 2},
    )
    assert approved.status_code == 200
    assert approved.json()["document"]["accounting"]["external_write_performed"] is False


def test_unknown_submitter_and_stale_review_are_rejected(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    invalid = client.post(
        "/api/aion/business/finance-inbox/acme/documents",
        data={"submitted_by_person_id": "person.unknown"},
        files={"file": ("receipt.png", b"image", "image/png")},
    )
    assert invalid.status_code == 422
    upload = client.post(
        "/api/aion/business/finance-inbox/acme/documents",
        data={"submitted_by_person_id": "person.worker"},
        files={"file": ("receipt.png", b"different-image", "image/png")},
    ).json()
    conflict = client.put(
        f"/api/aion/business/finance-inbox/acme/documents/{upload['document']['id']}/review",
        json={"expected_revision": 0, "fields": {}},
    )
    assert conflict.status_code == 409


def test_channels_advertise_current_and_future_phone_email_paths(tmp_path, monkeypatch):
    payload = _client(tmp_path, monkeypatch).get("/api/aion/business/finance-inbox/channels").json()
    statuses = {item["id"]: item["status"] for item in payload["channels"]}
    assert statuses["desktop_upload"] == "enabled"
    assert statuses["mobile_photo"] == "planned"
    assert statuses["agent_mailbox"] == "planned"
