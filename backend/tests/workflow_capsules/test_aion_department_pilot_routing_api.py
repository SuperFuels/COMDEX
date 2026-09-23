from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentAction,
    canonical_contract_hash,
)
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    approve_assignment_package,
    create_assignment_package,
    create_context_reference,
    create_provenance,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotRepository,
)


def _client(tmp_path, monkeypatch):
    task_repository = DepartmentPilotRepository(tmp_path / "department_runtime")
    container_repository = BusinessContainerRepository(tmp_path / "business_containers")
    monkeypatch.setattr(api, "get_department_pilot_repository", lambda: task_repository)
    monkeypatch.setattr(api, "get_business_container_repository", lambda: container_repository)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app), task_repository, container_repository


def _approved_package(department_id: str = "finance", context_refs=None):
    package = _draft_package(department_id, context_refs)
    return approve_assignment_package(
        package,
        approval_id=f"approval-{department_id}",
        approved_by="kevin",
        approved_at="2026-07-16T22:31:00+00:00",
    )


def _draft_package(department_id: str = "finance", context_refs=None):
    provenance = create_provenance(
        created_by="boardroom",
        created_at="2026-07-16T22:30:00+00:00",
        source_system="aion_boardroom",
    )
    package = create_assignment_package(
        package_id=f"package-{department_id}-routing",
        workspace_id="home-fixed",
        business_id="home-fixed",
        boardroom_session_id="session-routing",
        boardroom_decision_id=f"decision-{department_id}",
        title=f"{department_id.title()} assignment",
        objective=f"Route approved work to {department_id}.",
        department_id=department_id,
        actions=[
            BoardroomAssignmentAction(
                action_id=f"action-{department_id}-001",
                title=f"Prepare {department_id} analysis",
                objective=f"Prepare source-grounded {department_id} analysis.",
                department_id=department_id,
                capability=("cashflow.model" if department_id == "finance" else "pipeline.plan"),
            )
        ],
        context_refs=context_refs or [],
        provenance=provenance,
    )
    return package


def test_profiles_enable_finance_sales_support_and_hr_and_preserve_remaining_design_gates(tmp_path, monkeypatch):
    client, _, _ = _client(tmp_path, monkeypatch)
    response = client.get("/api/aion/business/department-pilots/profiles")
    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled_department_ids"] == ["finance", "sales", "support", "hr"]
    assert payload["design_required_department_ids"] == [
        "marketing",
        "operations",
    ]
    sales = next(item for item in payload["profiles"] if item["department_id"] == "sales")
    assert sales["activation_state"] == "enabled"
    assert "sales.qualification" in sales["allowed_capabilities"]
    hr = next(item for item in payload["profiles"] if item["department_id"] == "hr")
    assert hr["activation_state"] == "enabled"
    assert "visual organisation chart and accountability canvas" in hr["design_topics"]
    operations = next(
        item for item in payload["profiles"] if item["department_id"] == "operations"
    )
    assert operations["implementation_order"] == 6


def test_central_pilot_routes_approved_finance_package_idempotently(tmp_path, monkeypatch):
    client, repository, _ = _client(tmp_path, monkeypatch)
    package = _approved_package()
    request = {
        "package": package.model_dump(mode="json"),
        "routed_at": "2026-07-16T22:32:00+00:00",
        "routed_by": "central_pilot",
    }
    first = client.post("/api/aion/business/department-pilots/route", json=request)
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["routing_state"] == "routed_to_specialist_pilot"
    assert first_payload["task_count"] == 1
    task = first_payload["tasks"][0]["task"]
    assert task["pilot_id"] == "finance_pilot"
    assert task["status"] == "queued"

    second = client.post("/api/aion/business/department-pilots/route", json=request)
    assert second.status_code == 200
    assert second.json()["tasks"][0]["envelope_hash"] == first_payload["tasks"][0][
        "envelope_hash"
    ]
    assert len(repository.list_for_workspace("home-fixed")) == 1

    monitor = client.get("/api/aion/business/department-pilots/monitor/home-fixed")
    assert monitor.status_code == 200
    assert monitor.json()["status_counts"] == {"queued": 1}

    task_id = task["task_id"]
    claimed = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/transition",
        json={
            "to_status": "claimed",
            "occurred_at": "2026-07-16T22:33:00+00:00",
            "actor_id": "finance_pilot",
            "event_id": "event-finance-claimed",
        },
    )
    assert claimed.status_code == 200
    assert claimed.json()["task"]["status"] == "claimed"


def test_boardroom_approval_is_one_transaction_with_finance_queue_delivery(
    tmp_path, monkeypatch
):
    client, repository, _ = _client(tmp_path, monkeypatch)
    package = _draft_package()
    response = client.post(
        "/api/aion/business/department-pilots/approve-and-route",
        json={
            "package": package.model_dump(mode="json"),
            "approval_id": "approval-finance-one-step",
            "approved_by": "kevin",
            "approved_at": "2026-07-16T22:31:00+00:00",
            "approval_notes": "Approved in the Boardroom.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["approval_state"] == "approved_and_routed"
    assert payload["routing_state"] == "routed_to_specialist_pilot"
    assert payload["approved_package"]["status"] == "approved"
    assert payload["approved_package"]["approval"]["approved_by"] == "kevin"
    assert payload["tasks"][0]["task"]["pilot_id"] == "finance_pilot"
    assert len(repository.list_for_workspace("home-fixed")) == 1


def test_boardroom_action_endpoint_builds_canonical_package_server_side(
    tmp_path, monkeypatch
):
    client, repository, _ = _client(tmp_path, monkeypatch)
    response = client.post(
        "/api/aion/business/department-pilots/approve-boardroom-action",
        json={
            "workspace_id": "home-fixed",
            "business_id": "home-fixed",
            "boardroom_session_id": "session-real-boardroom",
            "boardroom_decision_id": "decision-protect-cash",
            "package_id": "package-finance-protect-cash",
            "title": "Protect the cash position",
            "objective": "Prepare a source-grounded 13-week cash view.",
            "department_id": "finance",
            "actions": [
                {
                    "action_id": "action-cash-forecast",
                    "title": "Prepare 13-week cash forecast",
                    "objective": "Show base, downside and recovery cash scenarios.",
                    "department_id": "finance",
                    "capability": "cashflow.model",
                    "priority": "high",
                    "acceptance_criteria": ["Every material figure shows provenance"],
                }
            ],
            "approval_id": "approval-real-boardroom",
            "approved_by": "kevin",
            "approved_at": "2026-07-16T22:40:00+00:00",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["approval_state"] == "boardroom_action_approved_and_routed"
    assert payload["approved_package"]["package_hash"].startswith("sha256:")
    assert payload["approved_package"]["provenance"]["source_system"] == "aion_boardroom"
    assert payload["tasks"][0]["task"]["status"] == "queued"
    assert len(repository.list_for_department("home-fixed", "finance")) == 1


def test_real_boardroom_action_hash_binds_current_finance_context(
    tmp_path, monkeypatch
):
    client, repository, containers = _client(tmp_path, monkeypatch)
    identity = {
        "id": "home-fixed.business_identity",
        "workspace_id": "home-fixed",
        "kind": "business_identity",
        "trading_name": "Home Fixed",
    }
    financial_model = {
        "id": "home-fixed.business_financial_model",
        "workspace_id": "home-fixed",
        "kind": "business_financial_model",
        "model_status": "accepted",
        "currency": "EUR",
        "metrics": {"revenue": 378750},
        "revision": 4,
    }
    containers.save_dict("home-fixed", "business_identity", identity)
    containers.save_dict(
        "home-fixed", "business_financial_model", financial_model
    )

    response = client.post(
        "/api/aion/business/department-pilots/approve-boardroom-action",
        json={
            "workspace_id": "home-fixed",
            "business_id": "home-fixed",
            "boardroom_session_id": "session-live-finance",
            "boardroom_decision_id": "decision-live-finance",
            "package_id": "package-live-finance",
            "title": "Review Finance performance",
            "objective": "Prepare a source-grounded Finance report.",
            "department_id": "finance",
            "actions": [
                {
                    "action_id": "action-live-finance",
                    "title": "Prepare management report",
                    "objective": "Explain revenue and cash performance.",
                    "department_id": "finance",
                    "capability": "finance.boardroom_analysis",
                }
            ],
            "approval_id": "approval-live-finance",
            "approved_by": "founder:kevin",
            "approved_at": "2026-07-20T10:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["context_binding_state"] == "hash_bound_at_boardroom_approval"
    assert payload["context_reference_count"] == 2
    references = payload["approved_package"]["context_refs"]
    assert {item["container_kind"] for item in references} == {
        "business_identity",
        "business_financial_model",
    }
    assert all(item["content_hash"].startswith("sha256:") for item in references)

    task_id = payload["tasks"][0]["task"]["task_id"]
    retrieved = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/retrieve-context",
        json={
            "retrieved_at": "2026-07-20T10:01:00+00:00",
            "retrieved_by": "finance_pilot",
        },
    )
    assert retrieved.status_code == 200
    evidence = retrieved.json()["retrieved_evidence"]
    assert {item["retrieval_status"] for item in evidence} == {"retrieved"}
    restored = repository.load("home-fixed", "finance", task_id)
    assert len(restored.retrieved_evidence) == 2


def test_unapproved_function_design_cannot_be_bypassed_by_router(tmp_path, monkeypatch):
    client, repository, _ = _client(tmp_path, monkeypatch)
    marketing = _approved_package("marketing")
    response = client.post(
        "/api/aion/business/department-pilots/route",
        json={
            "package": marketing.model_dump(mode="json"),
            "routed_at": "2026-07-16T22:32:00+00:00",
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "department_pilot_design_required"
    assert detail["department_id"] == "marketing"
    assert "campaign planning and day-to-day operating view" in detail["design_topics"]
    assert repository.list_for_workspace("home-fixed") == []


def test_finance_context_endpoint_retrieves_exact_container_and_persists_it(
    tmp_path, monkeypatch
):
    client, repository, containers = _client(tmp_path, monkeypatch)
    model = {
        "id": "home-fixed.business_financial_model",
        "workspace_id": "home-fixed",
        "kind": "business_financial_model",
        "model_status": "accepted",
        "currency": "EUR",
        "metrics": {"revenue": 378750},
        "revision": 4,
    }
    containers.save_dict("home-fixed", "business_financial_model", model)
    reference = create_context_reference(
        reference_id="finance-r4",
        workspace_id="home-fixed",
        container_kind="business_financial_model",
        container_id="home-fixed.business_financial_model",
        revision=4,
        content_hash=canonical_contract_hash(model),
        verification_state="source_backed",
    )
    package = _approved_package(context_refs=[reference])
    routed = client.post(
        "/api/aion/business/department-pilots/route",
        json={
            "package": package.model_dump(mode="json"),
            "routed_at": "2026-07-16T22:32:00+00:00",
        },
    ).json()
    task_id = routed["tasks"][0]["task"]["task_id"]
    response = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/retrieve-context",
        json={
            "retrieved_at": "2026-07-16T22:34:00+00:00",
            "retrieved_by": "finance_pilot",
        },
    )
    assert response.status_code == 200
    evidence = response.json()["retrieved_evidence"][0]
    assert evidence["retrieval_status"] == "retrieved"
    assert evidence["data"]["metrics"]["revenue"] == 378750
    restored = repository.load("home-fixed", "finance", task_id)
    assert restored.retrieved_evidence[0].retrieval_hash == evidence["retrieval_hash"]
