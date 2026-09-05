from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.medium_business_operating_service import MediumBusinessOperatingService


def model():
    return {
        "group": {"id": "group.food", "name": "Food Group"},
        "identity_providers": [{"id": "directory.corporate", "name": "Corporate SSO", "status": "active", "assurance": "mfa"}],
        "entities": [
            {"id": "entity.uk", "name": "Food UK Ltd", "status": "active", "country": "GB", "boardroom_workspace_id": "boardroom.food-uk", "business_map_ref": "map://food/uk"},
            {"id": "entity.es", "name": "Food España SL", "status": "active", "country": "ES", "boardroom_workspace_id": "boardroom.food-es", "business_map_ref": "map://food/es"},
        ],
        "units": [
            {"id": "unit.fresh", "name": "Fresh", "entity_id": "entity.uk", "kind": "division"},
            {"id": "unit.produce", "name": "Produce", "entity_id": "entity.uk", "kind": "business_unit", "parent_unit_id": "unit.fresh"},
            {"id": "unit.restaurant", "name": "Restaurants", "entity_id": "entity.es", "kind": "division"},
        ],
        "locations": [
            {"id": "location.london", "name": "London", "entity_id": "entity.uk", "region": "uk-south"},
            {"id": "location.almeria", "name": "Almería", "entity_id": "entity.es", "region": "eu-south"},
        ],
        "roles": [
            {"id": "role.group_owner", "capabilities": ["portfolio.read", "project.approve", "project.request", "department.route", "support.bundle.export", "audit.export"], "approval_limit": None},
            {"id": "role.experience", "capabilities": ["project.read", "project.request", "department.route"], "approval_limit": 0},
            {"id": "role.project_approver", "capabilities": ["project.read", "project.approve"], "approval_limit": 25_000},
            {"id": "role.adviser", "capabilities": ["project.read"], "approval_limit": 0},
        ],
        "projects": [
            {
                "id": "project.customer-experience",
                "name": "Customer Experience Relaunch",
                "entity_id": "entity.uk",
                "unit_id": "unit.fresh",
                "currency": "GBP",
                "budget": 100_000,
                "committed": 45_000,
                "actual": 30_000,
                "forecast_at_completion": 92_000,
                "model_expenditure": 400,
                "team": [
                    {"person_id": "person.experience", "project_role": "project_lead", "allocation_percent": 60},
                    {"person_id": "person.adviser", "project_role": "external_adviser", "allocation_percent": 20},
                ],
                "milestones": [{"id": "m1", "name": "Pilot", "status": "on_track"}],
                "risks": [{"id": "risk1", "title": "Supplier timing", "status": "open"}],
            },
            {
                "id": "project.restaurant-launch",
                "name": "Restaurant Launch",
                "entity_id": "entity.es",
                "unit_id": "unit.restaurant",
                "currency": "EUR",
                "budget": 200_000,
                "committed": 180_000,
                "actual": 160_000,
                "forecast_at_completion": 215_000,
                "team": [{"person_id": "person.owner", "project_role": "sponsor"}],
                "milestones": [],
                "risks": [],
            },
        ],
        "people": [
            {
                "id": "person.owner", "name": "Owner", "position_title": "Group Managing Director",
                "engagement_type": "director", "status": "active", "role_ids": ["role.group_owner"],
                "identity_subjects": [{"provider": "directory.corporate", "subject": "owner@example.test"}],
                "scopes": {"entity_ids": ["*"], "unit_ids": ["*"], "location_ids": ["*"], "project_ids": ["*"]},
            },
            {
                "id": "person.experience", "name": "Casey", "position_title": "Head of Experience",
                "engagement_type": "employee", "status": "active", "manager_id": "person.owner",
                "dotted_line_manager_ids": ["person.approver"],
                "role_ids": ["role.experience"],
                "scopes": {"entity_ids": ["entity.uk"], "unit_ids": ["unit.fresh"], "location_ids": ["location.london"], "project_ids": ["project.customer-experience"]},
            },
            {
                "id": "person.approver", "name": "Morgan", "position_title": "Programme Controller",
                "engagement_type": "employee", "status": "active", "manager_id": "person.owner",
                "role_ids": ["role.project_approver"],
                "scopes": {"entity_ids": ["entity.uk"], "unit_ids": ["unit.fresh"], "location_ids": ["location.london"], "project_ids": ["project.customer-experience"]},
            },
            {
                "id": "person.adviser", "name": "Taylor", "position_title": "CX Research Adviser",
                "engagement_type": "freelancer", "status": "active", "manager_id": "person.experience",
                "role_ids": ["role.adviser"],
                "scopes": {"entity_ids": ["entity.uk"], "unit_ids": ["unit.fresh"], "location_ids": [], "project_ids": ["project.customer-experience"]},
            },
        ],
        "workflows": [
            {"id": "workflow.project-spend", "request_capability": "project.request", "approval_capability": "project.approve", "approval_limit": 25_000, "escalate_above": "person.owner", "project_id": "project.customer-experience"}
        ],
        "policies": {
            "separation_of_duty": [{"request_capability": "project.request", "approval_capability": "project.approve"}],
            "data_residency": {"restricted": ["eu", "uk"], "confidential": ["eu", "uk", "local"]},
            "provider_regions": {"customer-aws": ["eu-west-1", "eu-south-2"]},
            "retention_days": {"restricted": 365, "confidential": 730},
        },
    }


def configured(tmp_path):
    service = MediumBusinessOperatingService(tmp_path / "medium")
    saved = service.configure(model(), expected_revision=0, changed_by="person.owner")
    return service, saved


def test_group_entities_divisions_locations_and_arbitrary_titles_are_canonical(tmp_path):
    service, saved = configured(tmp_path)
    assert saved["revision"] == 1
    assert len(saved["entities"]) == 2
    assert service._by_id(saved["units"], "unit.produce")["parent_unit_id"] == "unit.fresh"
    assert service._by_id(saved["people"], "person.experience")["position_title"] == "Head of Experience"
    assert saved["model_hash"]


def test_invalid_and_cyclic_hierarchies_fail_closed(tmp_path):
    service = MediumBusinessOperatingService(tmp_path / "medium")
    value = model()
    value["people"][0]["manager_id"] = "person.experience"
    with pytest.raises(ValueError, match="reporting_hierarchy_cycle"):
        service.configure(value, changed_by="owner")
    value = model()
    value["units"][0]["parent_unit_id"] = "unit.produce"
    with pytest.raises(ValueError, match="unit_hierarchy_cycle"):
        service.configure(value, changed_by="owner")


def test_project_budget_team_milestone_risk_and_forecast_position(tmp_path):
    service, _saved = configured(tmp_path)
    position = service.project_position("project.customer-experience")
    assert position["budget"] == 100_000
    assert position["remaining_after_commitments"] == 55_000
    assert position["forecast_variance"] == 8_000
    assert position["over_budget"] is False
    assert position["team_size"] == 2
    assert position["milestones"][0]["status"] == "on_track"
    assert service.project_position("project.restaurant-launch")["over_budget"] is True


def test_scope_amount_and_separation_of_duty_controls(tmp_path):
    service, _saved = configured(tmp_path)
    assert service.access_decision(person_id="person.approver", capability="project.approve", entity_id="entity.uk", project_id="project.customer-experience", amount=20_000)["allowed"] is True
    assert service.access_decision(person_id="person.approver", capability="project.approve", entity_id="entity.es", project_id="project.restaurant-launch", amount=10_000)["reason"] == "entity_id_out_of_scope"
    assert service.access_decision(person_id="person.approver", capability="project.approve", project_id="project.customer-experience", amount=30_000)["reason"] == "approval_limit_exceeded"
    conflict = service.access_decision(person_id="person.owner", capability="project.approve", project_id="project.customer-experience", amount=1_000, action_history=[{"person_id": "person.owner", "capability": "project.request"}])
    assert conflict["reason"] == "separation_of_duty_conflict"


def test_bounded_workspace_supports_employee_freelancer_adviser_and_director(tmp_path):
    service, _saved = configured(tmp_path)
    adviser = service.workspace_projection(person_id="person.adviser")
    assert adviser["person"]["engagement_type"] == "freelancer"
    assert [item["id"] for item in adviser["projects"]] == ["project.customer-experience"]
    assert adviser["private_other_people_excluded"] is True
    owner = service.workspace_projection(person_id="person.owner")
    assert len(owner["entities"]) == 2
    assert len(owner["projects"]) == 2


def test_portfolio_dashboard_is_viewer_scoped_and_reports_model_spend(tmp_path):
    service, _saved = configured(tmp_path)
    owner = service.portfolio_dashboard(viewer_id="person.owner")
    assert owner["totals_by_currency"]["GBP"]["budget"] == 100_000
    assert owner["totals_by_currency"]["EUR"]["forecast_at_completion"] == 215_000
    assert owner["cross_currency_total_suppressed"] is True
    assert owner["model_expenditure_by_currency"] == {"GBP": 400.0, "EUR": 0.0}
    assert owner["risks"][0]["id"] == "risk1"
    adviser = service.portfolio_dashboard(viewer_id="person.adviser")
    assert [item["project_id"] for item in adviser["projects"]] == ["project.customer-experience"]


def test_residency_and_regional_provider_policy_fail_closed(tmp_path):
    service, _saved = configured(tmp_path)
    allowed = service.route_policy(data_classification="restricted", residency="eu", provider="customer-aws", region="eu-west-1")
    assert allowed["allowed"] is True
    assert allowed["retention_days"] == 365
    denied = service.route_policy(data_classification="restricted", residency="us", provider="customer-aws", region="us-east-1")
    assert set(denied["reasons"]) == {"data_residency_not_allowed", "provider_region_not_allowed"}
    assert service.route_policy(data_classification="secret", residency="eu", provider="unknown", region="eu")["allowed"] is False


def test_support_bundle_and_customer_audit_are_redacted(tmp_path):
    service = MediumBusinessOperatingService(tmp_path / "medium")
    value = model()
    value["group"]["api_key"] = "must-never-export"
    service.configure(value, expected_revision=0, changed_by="person.owner")
    bundle = service.support_bundle(viewer_id="person.owner")
    assert bundle["secrets_included"] is False
    assert bundle["customer_content_included"] is False
    assert "must-never-export" not in json.dumps(bundle)
    audit = service.audit_export(viewer_id="person.owner")
    assert audit["event_count"] == 1
    assert "must-never-export" not in json.dumps(audit)


def test_revision_conflict_prevents_parallel_overwrite(tmp_path):
    service, _saved = configured(tmp_path)
    with pytest.raises(ValueError, match="revision_conflict"):
        service.configure(model(), expected_revision=0, changed_by="person.owner")


def test_department_route_binds_existing_boardroom_router_to_shared_map(tmp_path):
    service, _saved = configured(tmp_path)
    route = service.department_route(person_id="person.experience", entity_id="entity.uk", unit_id="unit.fresh", department="Experience", task_class="customer journey")
    assert route["allowed"] is True
    assert route["boardroom_workspace_id"] == "boardroom.food-uk"
    assert route["business_map_ref"] == "map://food/uk"
    assert service.department_route(person_id="person.experience", entity_id="entity.es", unit_id="unit.restaurant", department="Experience", task_class="review")["allowed"] is False


def test_workflow_requires_distinct_approver_and_escalates_above_limit(tmp_path):
    service, _saved = configured(tmp_path)
    accepted = service.workflow_decision(workflow_id="workflow.project-spend", requester_id="person.experience", approver_id="person.approver", amount=20_000)
    assert accepted["allowed"] is True
    same_person = service.workflow_decision(workflow_id="workflow.project-spend", requester_id="person.owner", approver_id="person.owner", amount=1_000)
    assert same_person["reason"] == "approver_separation_of_duty_conflict"
    escalated = service.workflow_decision(workflow_id="workflow.project-spend", requester_id="person.experience", approver_id="person.approver", amount=30_000)
    assert escalated["reason"] == "workflow_escalation_required"
    assert escalated["escalate_to"] == "person.owner"


def test_enterprise_identity_resolves_one_active_subject(tmp_path):
    service, _saved = configured(tmp_path)
    identity = service.resolve_identity(provider="directory.corporate", subject="owner@example.test")
    assert identity == {"allowed": True, "person_id": "person.owner", "position_title": "Group Managing Director", "assurance": "mfa"}
    assert service.resolve_identity(provider="directory.corporate", subject="unknown")["allowed"] is False
