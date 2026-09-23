from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService


def _service(tmp_path):
    return OrganizationAuthorityService(BusinessContainerRepository(tmp_path / "containers"))


def _model(service):
    model = service.empty("acme")
    model["departments"] = [
        {"id": "department.executive", "name": "Leadership", "status": "active"},
        {"id": "department.operations", "name": "Operations", "status": "active", "parent_department_id": "department.executive"},
    ]
    model["people"] = [
        {
            "id": "person.owner", "name": "Alex Owner", "email": "alex@example.com",
            "employment_type": "owner", "position_title": "Managing Director", "status": "active",
            "department_ids": ["department.executive"], "role_ids": ["role.owner_director"],
        },
        {
            "id": "person.worker", "name": "Sam Worker", "email": "sam@example.com",
            "employment_type": "employee", "position_title": "Installer", "status": "active",
            "manager_id": "person.owner", "department_ids": ["department.operations"],
            "role_ids": ["role.employee"],
        },
    ]
    model["assets"] = [{
        "id": "asset.card", "name": "Operations card", "asset_type": "company_card",
        "assigned_person_id": "person.worker", "last_four": "1234", "transaction_limit": 250,
    }]
    return model


def test_empty_model_is_safe_and_contains_templates(tmp_path):
    model = _service(tmp_path).get("acme")
    assert model["model_status"] == "setup_required"
    assert model["people"] == []
    assert any(role["id"] == "role.owner_director" for role in model["roles"])
    assert model["governance"]["job_title_does_not_grant_access"] is True


def test_save_builds_ready_authority_model_and_assigns_card(tmp_path):
    service = _service(tmp_path)
    saved = service.save("acme", _model(service), expected_revision=0, changed_by="test")
    assert saved["revision"] == 1
    assert saved["model_status"] == "authority_ready"
    assert saved["summary"]["active_people"] == 2
    assert saved["summary"]["assigned_cards"] == 1
    assert service.get("acme")["people"][1]["manager_id"] == "person.owner"


def test_confidential_workforce_costing_derives_effective_planning_rates(tmp_path):
    service = _service(tmp_path)
    model = _model(service)
    model["people"][1]["workforce_costing"] = {
        "basis": "monthly", "base_rate": 2800, "employer_on_cost_percent": 20,
        "monthly_bonus": 140, "productive_hours_month": 140, "hours_per_day": 8,
    }
    saved = service.save("acme", model)
    costing = saved["people"][1]["workforce_costing"]
    assert costing["effective_monthly_cost"] == 3500
    assert costing["effective_hourly_cost"] == 25
    assert costing["effective_daily_cost"] == 200
    assert costing["confidential"] is True
    assert saved["summary"]["workforce_costing_ready"] == 1


def test_access_is_role_scope_and_amount_aware(tmp_path):
    service = _service(tmp_path)
    model = _model(service)
    model["people"][1]["role_ids"] = ["role.department_manager"]
    service.save("acme", model)
    assert service.access_decision(
        "acme", person_id="person.worker", capability="expenses.approve",
        department_id="department.operations", amount=1200,
    )["allowed"] is True
    denied = service.access_decision(
        "acme", person_id="person.worker", capability="expenses.approve",
        department_id="department.operations", amount=3000,
    )
    assert denied["allowed"] is False
    assert denied["reason"] == "approval_limit_exceeded"
    assert service.access_decision(
        "acme", person_id="person.worker", capability="boardroom.view_full",
    )["allowed"] is False


def test_reporting_cycle_is_rejected(tmp_path):
    service = _service(tmp_path)
    model = _model(service)
    model["people"][0]["manager_id"] = "person.worker"
    with pytest.raises(ValueError, match="reporting_line_cycle"):
        service.save("acme", model)


def test_viewer_projection_redacts_employee_and_expands_owner(tmp_path):
    service = _service(tmp_path)
    service.save("acme", _model(service))
    employee = service.viewer_projection("acme", person_id="person.worker")
    assert employee["boardroom_sections"] == []
    assert employee["finance_data_classes"] == ["own_expenses"]
    owner = service.viewer_projection("acme", person_id="person.owner")
    assert "finance" in owner["boardroom_sections"]
    assert "transaction_detail" in owner["finance_data_classes"]


def test_revision_conflict_prevents_overwrite(tmp_path):
    service = _service(tmp_path)
    service.save("acme", _model(service), expected_revision=0)
    with pytest.raises(ValueError, match="organization_revision_conflict"):
        service.save("acme", _model(service), expected_revision=0)


def test_people_operations_persist_only_for_known_people_and_remain_human_gated(tmp_path):
    service = _service(tmp_path)
    model = _model(service)
    model["people_operations"] = {
        "leave_requests": [
            {"id": "leave.1", "person_id": "person.worker", "status": "requested", "start_date": "2026-09-01", "end_date": "2026-09-02"},
            {"id": "leave.bad", "person_id": "person.unknown", "status": "approved"},
        ],
        "appraisals": [{"id": "review.1", "person_id": "person.worker", "due_date": "2026-09-30"}],
        "escalations": [{"id": "issue.1", "person_id": "person.worker", "status": "open", "restricted": True}],
    }
    saved = service.save("acme", model)
    ops = saved["people_operations"]
    assert [item["id"] for item in ops["leave_requests"]] == ["leave.1"]
    assert saved["summary"]["pending_leave_requests"] == 1
    assert saved["summary"]["open_people_escalations"] == 1
    assert ops["governance"]["human_employment_decisions_required"] is True
    assert ops["governance"]["sensitive_detail_excluded_from_dashboard"] is True
