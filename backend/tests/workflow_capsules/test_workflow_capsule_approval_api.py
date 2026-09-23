from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.workflow_capsule_router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_workflow_capsule_api_run_dry_lists_and_approves_then_resumes_connector_ready() -> None:
    client = _client()

    dry_resp = client.post(
        "/api/workflow-capsules/run-dry",
        json={
            "value": "WG-001",
            "inputs": {"gmail_message_id": "api-demo-message-001"},
            "available_vault_requirements": [],
            "cau_state": {
                "allow_learn": False,
                "adr_active": False,
                "deny_reason": "pytest_api_no_learning",
            },
            "extra": {"pytest": True},
        },
    )

    assert dry_resp.status_code == 200
    dry = dry_resp.json()
    assert dry["ok"] is True
    assert dry["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert dry["approval"]["status"] == "pending"

    approval_id = dry["approval"]["approval_id"]

    list_resp = client.get("/api/workflow-capsules/approvals", params={"status": "pending"})
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert listed["ok"] is True
    assert any(item["approval_id"] == approval_id for item in listed["items"])

    approve_resp = client.post(
        f"/api/workflow-capsules/approvals/{approval_id}/approve",
        json={
            "decided_by": "pytest",
            "reason": "pytest approval API lock",
        },
    )

    assert approve_resp.status_code == 200
    approved = approve_resp.json()
    assert approved["ok"] is True
    assert approved["status"] == "approved"

    blocked_resp = client.post(
        f"/api/workflow-capsules/approvals/{approval_id}/resume",
        json={
            "available_vault_requirements": [],
            "cau_state": {"allow_learn": False},
        },
    )

    assert blocked_resp.status_code == 200
    blocked = blocked_resp.json()
    assert blocked["ok"] is False
    assert blocked["error"] == "missing_vault_requirements"

    ready_resp = client.post(
        f"/api/workflow-capsules/approvals/{approval_id}/resume",
        json={
            "available_vault_requirements": ["vault.gmail.credentials"],
            "cau_state": {"allow_learn": False},
        },
    )

    assert ready_resp.status_code == 200
    ready = ready_resp.json()
    assert ready["ok"] is True
    assert ready["execution_mode"] == "connector_ready"
    assert ready["status"] == "simulated_external_write_ready"
    assert ready["connector_result"]["status"] == "simulated_external_write_ready"


def test_workflow_capsule_api_reject_blocks_resume() -> None:
    client = _client()

    dry = client.post(
        "/api/workflow-capsules/run-dry",
        json={
            "value": "WG-001",
            "inputs": {"gmail_message_id": "api-demo-message-002"},
        },
    ).json()

    approval_id = dry["approval"]["approval_id"]

    reject_resp = client.post(
        f"/api/workflow-capsules/approvals/{approval_id}/reject",
        json={
            "decided_by": "pytest",
            "reason": "pytest reject path",
        },
    )

    assert reject_resp.status_code == 200
    rejected = reject_resp.json()
    assert rejected["ok"] is True
    assert rejected["status"] == "rejected"

    resume_resp = client.post(
        f"/api/workflow-capsules/approvals/{approval_id}/resume",
        json={
            "available_vault_requirements": ["vault.gmail.credentials"],
            "cau_state": {"allow_learn": False},
        },
    )

    assert resume_resp.status_code == 200
    resumed = resume_resp.json()
    assert resumed["ok"] is False
    assert resumed["error"] == "approval_not_approved"
