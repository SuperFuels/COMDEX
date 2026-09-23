from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotRepository,
)
from backend.modules.aion_business.runtime.finance_pilot_execution_service import (
    FinancePilotExecutionService,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)


def _isolate_runtime(tmp_path, monkeypatch) -> None:
    root = tmp_path / "aion_runtime"
    names = {
        "ROOT": root,
        "WORKSPACES": root / "workspaces",
        "CONTAINER_BINDINGS": root / "container_bindings",
        "BUSINESS_CONTAINERS": root / "business_containers",
        "ROLES": root / "roles",
        "AGENTS": root / "agents",
        "TASKS": root / "tasks",
        "LEARNING": root / "learning",
        "AUDIT": root / "audit",
        "FOUNDER_REVIEW": root / "founder_review",
        "EXTERNAL_SPECIALISTS": root / "external_specialists",
        "EXTERNAL_WORK_ORDERS": root / "external_work_orders",
        "TOPOLOGIES": root / "topologies",
        "DEPARTMENT_PILOT_RUNTIME": root / "department_pilot_runtime",
    }
    for name, value in names.items():
        monkeypatch.setattr(AIONBusinessPaths, name, value)


def _client(tmp_path, monkeypatch):
    _isolate_runtime(tmp_path, monkeypatch)
    tasks = DepartmentPilotRepository(tmp_path / "task_runtime")
    containers = BusinessContainerRepository(tmp_path / "business_containers")
    service = FinancePilotExecutionService(
        task_repository=tasks,
        container_repository=containers,
        artifact_root=tmp_path / "artifacts" / "home-fixed",
    )
    monkeypatch.setattr(api, "get_department_pilot_repository", lambda: tasks)
    monkeypatch.setattr(api, "get_business_container_repository", lambda: containers)
    monkeypatch.setattr(api, "FinancePilotExecutionService", lambda **_kwargs: service)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app), tasks, containers


def _seed_context(containers: BusinessContainerRepository) -> None:
    containers.save_dict(
        "home-fixed",
        "business_identity",
        {
            "id": "home-fixed.business_identity",
            "workspace_id": "home-fixed",
            "kind": "business_identity",
            "trading_name": "Home Fixed",
            "currency": "EUR",
            "revision": 2,
        },
    )
    containers.save_dict(
        "home-fixed",
        "business_financial_model",
        {
            "id": "home-fixed.business_financial_model",
            "workspace_id": "home-fixed",
            "kind": "business_financial_model",
            "currency": "EUR",
            "metrics": {
                "revenue": 378750,
                "gross_profit": 235016,
                "operating_profit": 152346,
                "ending_cash": 159011,
            },
            "missing_information": [],
            "revision": 5,
        },
    )
    containers.save_dict(
        "home-fixed",
        "business_operating_model",
        {
            "id": "home-fixed.business_operating_model",
            "workspace_id": "home-fixed",
            "kind": "business_operating_model",
            "offerings": [{"name": "Home repair services"}],
            "revision": 3,
        },
    )
    containers.save_dict(
        "home-fixed",
        "department_intelligence",
        {
            "id": "home-fixed.department_intelligence",
            "workspace_id": "home-fixed",
            "kind": "department_intelligence",
            "departments": {"finance": {"department": "finance"}},
            "revision": 7,
        },
    )
    containers.save_dict(
        "home-fixed",
        "boardroom_snapshot",
        {
            "id": "home-fixed.boardroom_snapshot",
            "workspace_id": "home-fixed",
            "kind": "boardroom_snapshot",
            "boardroom": {"runtime": {}},
            "revision": 1,
        },
    )


def _route_task(client: TestClient, capability: str = "finance.boardroom_analysis") -> str:
    response = client.post(
        "/api/aion/business/department-pilots/approve-boardroom-action",
        json={
            "workspace_id": "home-fixed",
            "business_id": "home-fixed",
            "boardroom_session_id": "session-finance-result",
            "boardroom_decision_id": "decision-finance-result",
            "package_id": "package-finance-result",
            "title": "Review financial performance",
            "objective": "Prepare a grounded management report for the next Board meeting.",
            "department_id": "finance",
            "actions": [
                {
                    "action_id": "action-finance-result",
                    "title": "Prepare management report",
                    "objective": "Explain revenue, profit and cash using approved evidence.",
                    "department_id": "finance",
                    "capability": capability,
                }
            ],
            "approval_id": "approval-finance-result",
            "approved_by": "founder:kevin",
            "approved_at": "2026-07-20T11:00:00+00:00",
        },
    )
    assert response.status_code == 200
    return response.json()["tasks"][0]["task"]["task_id"]


def test_finance_task_completes_with_artifact_intelligence_and_boardroom_handback(
    tmp_path, monkeypatch
):
    client, tasks, containers = _client(tmp_path, monkeypatch)
    _seed_context(containers)
    task_id = _route_task(client)

    response = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/execute-read-only",
        json={
            "actor_id": "finance_pilot",
            "executed_at": "2026-07-20T11:01:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_state"] == "completed_for_boardroom_handback"
    assert payload["report"]["metrics"] == {
        "currency": "EUR",
        "revenue": 378750.0,
        "gross_profit": 235016.0,
        "operating_profit": 152346.0,
        "ending_cash": 159011.0,
    }
    management = payload["report"]["management_accounts"]
    assert management["schema_version"] == "aion.finance_pilot.management_accounts.v2"
    assert management["headline"]["revenue"] == 378750.0
    assert management["comparison_coverage"]["budget_available"] is False
    assert management["comparison_coverage"]["previous_period_available"] is False
    envelope = tasks.load("home-fixed", "finance", task_id)
    assert envelope.task.status == "completed"
    assert envelope.handback is not None
    assert envelope.handback.status == "ready_for_boardroom"
    assert envelope.handback.metric_changes["management_report"]["headline"][
        "ending_cash"
    ] == 159011.0
    assert len(envelope.artifacts) == len(envelope.receipts) == 1
    report_path = envelope.artifacts[0].business_container_path
    assert (tmp_path / "artifacts" / "home-fixed" / "finance" / "reports").is_dir()
    assert report_path.endswith(".json")

    intelligence = containers.load_dict("home-fixed", "department_intelligence")
    result = intelligence["departments"]["finance"]["latest_pilot_result"]
    assert result["task_id"] == task_id
    assert result["status"] == "ready_for_boardroom"
    snapshot = containers.load_dict("home-fixed", "boardroom_snapshot")
    assert snapshot["boardroom"]["runtime"]["latest_department_pilot_handback"][
        "task_id"
    ] == task_id

    cabinet = WorkflowFileCabinetRepository.load("home-fixed")
    finance = next(item for item in cabinet["folders"] if item["name"] == "Finance")
    reports = next(item for item in finance["children"] if item["name"] == "Reports")
    assert reports["children"][0]["target"]["task_id"] == task_id

    repeated = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/execute-read-only",
        json={"executed_at": "2026-07-20T11:02:00+00:00"},
    )
    assert repeated.status_code == 200
    restored = tasks.load("home-fixed", "finance", task_id)
    assert len(restored.artifacts) == len(restored.receipts) == 1
    assert repeated.json()["envelope"]["envelope_hash"] == restored.envelope_hash


def test_finance_executor_rejects_unapproved_capability_without_claiming_task(
    tmp_path, monkeypatch
):
    client, tasks, containers = _client(tmp_path, monkeypatch)
    _seed_context(containers)
    task_id = _route_task(client, capability="finance.pay_supplier")

    response = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/execute-read-only",
        json={},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "finance_pilot_permission_denied"
    assert tasks.load("home-fixed", "finance", task_id).task.status == "queued"
    assert not (tmp_path / "artifacts").exists()


def test_finance_execution_retrieves_period_budget_and_comparative_context(
    tmp_path, monkeypatch
):
    client, _tasks, containers = _client(tmp_path, monkeypatch)
    _seed_context(containers)
    model = containers.load_dict("home-fixed", "business_financial_model")
    model["reporting_period"] = {
        "label": "Year ended 31 December 2025",
        "from": "2025-01-01",
        "to": "2025-12-31",
    }
    model["reporting_periods"] = {
        "current": {"metrics": model["metrics"]},
        "budget": {
            "metrics": {
                "revenue": 350000,
                "gross_profit": 210000,
                "operating_profit": 135000,
                "ending_cash": 140000,
            }
        },
        "previous": {
            "metrics": {
                "revenue": 320000,
                "gross_profit": 190000,
                "operating_profit": 120000,
                "ending_cash": 115000,
            }
        },
    }
    model["evidence_refs"] = [
        {
            "source": "accepted_management_accounts",
            "accepted_at": "2026-07-18T12:00:00+00:00",
            "verification_status": "accepted_from_source_document",
        }
    ]
    model["revision"] = 6
    containers.save_dict("home-fixed", "business_financial_model", model)
    task_id = _route_task(client)

    response = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/execute-read-only",
        json={"executed_at": "2026-07-20T12:00:00+00:00"},
    )

    assert response.status_code == 200
    management = response.json()["report"]["management_accounts"]
    assert management["period"]["label"] == "Year ended 31 December 2025"
    assert management["comparison_coverage"]["budget_available"] is True
    assert management["comparison_coverage"]["previous_period_available"] is True
    revenue = next(item for item in management["kpis"] if item["key"] == "revenue")
    assert revenue["budget_variance"] == 28750
    assert revenue["previous_variance"] == 58750
    assert management["evidence_freshness"]["overall_state"] == "fresh"
