from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.modules.aion_business.runtime.project_management_service import ProjectManagementService


def service(tmp_path) -> ProjectManagementService:
    class OfflineRouter:
        def generate(self, **_kwargs):
            return SimpleNamespace(ok=False, content="", provider=None, model=None, error_code="offline_test")
    return ProjectManagementService(root=tmp_path / "business-containers", provider_router=OfflineRouter())


def create_project(projects: ProjectManagementService, workspace: str = "workspace-a") -> dict:
    state = projects.create_project(workspace, {
        "title": "Client office refurbishment",
        "outcome": "Deliver a usable office with approved finishes before the client move-in date.",
        "project_type": "refurbishment",
        "owner": "Delivery lead",
        "customer": "Example Client",
        "target_date": "2026-11-30",
        "currency": "GBP",
        "budget_total": "50000",
    }, actor_id="owner")
    return state["projects"][0]


def test_project_record_is_durable_and_workspace_scoped(tmp_path):
    projects = service(tmp_path)
    project = create_project(projects)

    assert project["project_type"] == "refurbishment"
    assert project["financials"]["remaining"] == "50000.00"
    assert projects.load("workspace-a")["projects"][0]["id"] == project["id"]
    assert projects.load("workspace-b")["projects"] == []


def test_delivery_actions_keep_tasks_resources_risks_and_decisions_together(tmp_path):
    projects = service(tmp_path)
    project = create_project(projects)
    project_id = project["id"]

    state = projects.apply_action("workspace-a", project_id, "add_task", {
        "title": "Confirm electrical scope", "assignee": "Site manager", "due_date": "2026-10-10",
    }, actor_id="owner")
    task_id = state["projects"][0]["tasks"][0]["id"]
    projects.apply_action("workspace-a", project_id, "task_status", {"task_id": task_id, "status": "done"}, actor_id="owner")
    projects.apply_action("workspace-a", project_id, "add_milestone", {"title": "First fix complete", "due_date": "2026-10-31"}, actor_id="owner")
    projects.apply_action("workspace-a", project_id, "add_resource", {"name": "Flooring supplier", "kind": "supplier", "quantity": "120 sqm"}, actor_id="owner")
    projects.apply_action("workspace-a", project_id, "add_risk", {"title": "Long lead-time flooring", "impact": "high", "mitigation": "Approve samples this week"}, actor_id="owner")
    final = projects.apply_action("workspace-a", project_id, "add_decision", {"decision": "Use alternate finish", "reason": "Meets programme and budget"}, actor_id="owner")
    record = final["projects"][0]

    assert record["progress_percent"] == 100
    assert record["resources"][0]["kind"] == "supplier"
    assert record["open_risk_count"] == 1
    assert record["decisions"][0]["reason"] == "Meets programme and budget"
    assert len(record["activity"]) == 7


def test_budget_separates_spent_from_committed_and_derives_remaining(tmp_path):
    projects = service(tmp_path)
    project_id = create_project(projects)["id"]
    projects.apply_action("workspace-a", project_id, "record_cost", {
        "description": "Design fee", "amount": "2500", "category": "supplier", "committed": False,
    }, actor_id="owner")
    state = projects.apply_action("workspace-a", project_id, "record_cost", {
        "description": "Materials order", "amount": "10000", "category": "materials", "committed": True,
    }, actor_id="owner")
    project = state["projects"][0]

    assert project["financials"] == {
        "spent": "2500.00", "committed": "10000.00", "forecast_total": "12500.00", "remaining": "37500.00",
    }
    assert Decimal(state["summary"]["remaining_total"]) == Decimal("37500.00")


def test_invalid_money_task_status_and_missing_project_fail_closed(tmp_path):
    projects = service(tmp_path)
    project_id = create_project(projects)["id"]
    with pytest.raises(ValueError, match="invalid_money_amount"):
        projects.apply_action("workspace-a", project_id, "record_cost", {"description": "Bad", "amount": "many"}, actor_id="owner")
    state = projects.apply_action("workspace-a", project_id, "add_task", {"title": "Test"}, actor_id="owner")
    with pytest.raises(ValueError, match="invalid_task_status"):
        projects.apply_action("workspace-a", project_id, "task_status", {"task_id": state["projects"][0]["tasks"][0]["id"], "status": "maybe"}, actor_id="owner")
    with pytest.raises(LookupError, match="project_not_found"):
        projects.apply_action("workspace-a", "not-present", "update", {}, actor_id="owner")


def test_task_fields_can_be_edited_without_replacing_the_task_record(tmp_path):
    projects = service(tmp_path)
    project_id = create_project(projects)["id"]
    created = projects.apply_action("workspace-a", project_id, "add_task", {
        "title": "Confirm scope", "assignee": "Project lead", "due_date": "2026-10-10",
    }, actor_id="owner")
    task_id = created["projects"][0]["tasks"][0]["id"]

    state = projects.apply_action("workspace-a", project_id, "update_task", {
        "task_id": task_id, "title": "Confirm final scope", "assignee": "Site manager",
        "start_date": "2026-10-01", "due_date": "2026-10-12", "priority": "high",
        "estimated_cost": "1750", "status": "in_progress",
    }, actor_id="delivery-lead")
    task = state["projects"][0]["tasks"][0]

    assert task["id"] == task_id
    assert task["title"] == "Confirm final scope"
    assert task["status"] == "in_progress"
    assert task["estimated_cost"] == "1750.00"
    assert task["updated_by"] == "delivery-lead"


def test_general_projects_task_dependencies_and_file_links_are_durable(tmp_path):
    projects = service(tmp_path)
    state = projects.create_project("workspace-a", {
        "title": "Launch customer portal", "outcome": "Customers can manage their account online.",
        "project_type": "software_project", "start_date": "2026-10-01",
    }, actor_id="owner")
    project_id = state["projects"][0]["id"]
    first = projects.apply_action("workspace-a", project_id, "add_task", {
        "title": "Approve user journeys", "start_date": "2026-10-01", "due_date": "2026-10-05",
        "description": "Signed-off journeys are attached.",
    }, actor_id="owner")
    first_id = first["projects"][0]["tasks"][0]["id"]
    second = projects.apply_action("workspace-a", project_id, "add_task", {
        "title": "Build account screen", "dependency_ids": [first_id], "due_date": "2026-10-12",
    }, actor_id="owner")
    final = projects.apply_action("workspace-a", project_id, "add_file", {
        "name": "portal-brief.pdf", "mime_type": "application/pdf", "size": 4096,
    }, actor_id="owner")

    assert second["projects"][0]["tasks"][1]["dependency_ids"] == [first_id]
    assert final["projects"][0]["project_type"] == "software_project"
    assert final["projects"][0]["files"][0]["name"] == "portal-brief.pdf"


def test_investigation_reports_only_recorded_portfolio_evidence(tmp_path):
    projects = service(tmp_path)
    project_id = create_project(projects)["id"]
    projects.apply_action("workspace-a", project_id, "update", {"status": "at_risk"}, actor_id="owner")
    answer = projects.investigate("workspace-a", "What needs my attention?")

    assert "1 at risk or blocked" in answer["answer"]
    assert "Client office refurbishment" in answer["answer"]
    assert answer["project_ids"] == [project_id]


def test_project_pilot_creates_and_completes_tasks_from_plain_language(tmp_path):
    projects = service(tmp_path)
    project_id = create_project(projects)["id"]

    first = projects.agent_turn(
        "workspace-a", "Pilot create a new task to pick up hammer and take it to the job to work",
        project_id=project_id, actor_id="owner",
    )
    assert first["action"] == "needs_clarification"
    assert first["draft"]["task_title"] == "pick up hammer and take it to the job to work"
    assert "When should" in first["reply"]

    second = projects.agent_turn(
        "workspace-a", "tomorrow", project_id=project_id, actor_id="owner",
    )
    assert second["action"] == "needs_clarification"
    assert "Who is accountable" in second["reply"]

    created = projects.agent_turn(
        "workspace-a", "Kevin", project_id=project_id, actor_id="owner",
    )
    task = created["state"]["projects"][0]["tasks"][0]
    assert created["action"] == "task_added"
    assert task["title"] == "pick up hammer and take it to the job to work"
    assert task["due_date"]
    assert task["assignee"] == "Kevin"
    assert task["work_mode"] == "manual"

    completed = projects.agent_turn(
        "workspace-a", "Mark pick up hammer and take it to the job to work as completed",
        project_id=project_id, actor_id="owner",
    )
    assert completed["action"] == "task_completed"
    assert completed["state"]["projects"][0]["tasks"][0]["status"] == "done"


def test_external_agent_work_is_scheduled_but_not_executed(tmp_path):
    projects = service(tmp_path)
    project_id = create_project(projects)["id"]

    result = projects.agent_turn(
        "workspace-a", "Ask Finance to send the client invoice on the 15th",
        project_id=project_id, actor_id="owner",
    )
    task = result["state"]["projects"][0]["tasks"][0]
    assert task["work_mode"] == "delegated"
    assert task["assigned_department"] == "finance"
    assert task["approval_required"] is True
    assert task["execution_status"] == "awaiting_approval"
    assert "waiting for approval" in result["reply"]


def test_project_pilot_requires_an_active_project_before_mutating(tmp_path):
    projects = service(tmp_path)
    result = projects.agent_turn("workspace-a", "Add a task to prepare the brief", actor_id="owner")
    assert result["action"] == "needs_project"
    assert result["changed"] is False


def test_project_pilot_uses_structured_model_plan_before_execution(tmp_path):
    class ModelRouter:
        def generate(self, **kwargs):
            assert kwargs["role_type"] == "PROJECTS"
            return SimpleNamespace(
                ok=True, provider="local", model="test-project-model", error_code=None,
                content='{"intent":"create_task","task_title":"pilot create a new task to collect materials","due_date":"2026-10-03","assignee":"Kevin","department":"","work_mode":"manual","external_action":false,"agent_instruction":"collect materials","missing_fields":[],"question":"","referenced_task":"","confidence":0.96}',
            )

    projects = ProjectManagementService(
        root=tmp_path / "business-containers", provider_router=ModelRouter(),
    )
    project_id = create_project(projects)["id"]
    result = projects.agent_turn(
        "workspace-a", "Could you sort out collecting the materials?",
        project_id=project_id, actor_id="owner",
    )
    task = result["state"]["projects"][0]["tasks"][0]
    assert result["planner"]["source"] == "project_pilot_model"
    assert result["planner"]["model"] == "test-project-model"
    assert task["title"] == "collect materials"
    assert task["assignee"] == "Kevin"
