import io
from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from backend.modules.aion_business.api import business_twin_data_api as api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService


def test_canonical_business_id_is_shared_and_rejects_global_targets():
    assert canonical_business_id("Home_Fixed") == "home-fixed"
    assert canonical_business_id("home-fixed") == "home-fixed"
    for invalid in ["", "global", "root", "tmp", "business_not_registered"]:
        with pytest.raises(ValueError):
            canonical_business_id(invalid)


def test_foundation_commits_identity_structure_map_and_ledger(tmp_path, monkeypatch):
    containers = tmp_path / "business_containers"
    workspaces = tmp_path / "workspaces"
    repository = BusinessContainerRepository(base_dir=containers)
    workspace_repository = WorkspaceRepository(base_dir=workspaces)
    monkeypatch.setattr(api, "_repo", lambda: repository)
    monkeypatch.setattr(api, "_workspaces", lambda: workspace_repository)

    response = api.commit_foundation(
        "Home_Fixed",
        api.FoundationCommitRequest(
            packet={
                "schema_version": "aion.business_foundation_discovery_packet.test",
                "foundation_draft": {
                    "business_name": "Home Fixed",
                    "user_name": "Kevin",
                    "business_type": "services",
                    "offer_summary": "Home repair services",
                    "target_customers": "Expats in Almeria",
                },
                "business_map": {
                    "facts": [{"field": "business_name", "value": "Home Fixed", "source": "voice_discovery"}],
                    "assumptions": [],
                    "unanswered_fields": [],
                    "department_discovery_gaps": ["finance"],
                },
            }
        ),
    )

    assert response["ok"] is True
    assert response["business_id"] == "home-fixed"
    assert repository.load_business_identity("home-fixed").legal_name == "Home Fixed"
    assert repository.load_business_structure("home-fixed").services[0]["description"] == "Home repair services"
    assert repository.load_business_map("home-fixed").facts[0]["source"] == "voice_discovery"
    assert repository.load_department_intelligence("home-fixed").departments["finance"]["status"] == "needs_discovery"

    business_root = containers / "home-fixed"
    sales_opportunity = business_root / "sales" / "revenue_spine" / "opportunities" / "opportunity-1.json"
    sales_opportunity.parent.mkdir(parents=True, exist_ok=True)
    sales_opportunity.write_text('{"opportunity_id":"opportunity-1"}', encoding="utf-8")
    support_case = business_root / "support" / "case_management" / "cases" / "case-1.json"
    support_case.parent.mkdir(parents=True, exist_ok=True)
    support_case.write_text('{"case_id":"case-1"}', encoding="utf-8")
    support_setup = business_root / "support" / "case_management" / "agent_setup.json"
    support_setup.write_text('{"approval_gated":true}', encoding="utf-8")

    appended = api.append_business_map_facts(
        "home-fixed",
        api.BusinessMapFactsRequest(
            source="finance_pilot_test",
            facts=[{"function": "finance", "field": "monthly_revenue", "value": 4200, "source_ref": "turn_1"}],
        ),
    )
    assert appended["appended"] == 1
    before_noop = api.get_business_map("home-fixed")
    duplicate = api.append_business_map_facts(
        "home-fixed",
        api.BusinessMapFactsRequest(
            source="finance_pilot_test",
            facts=[{"function": "finance", "field": "monthly_revenue", "value": 4200, "source_ref": "turn_1"}],
        ),
    )
    after_noop = api.get_business_map("home-fixed")
    assert duplicate["appended"] == 0
    assert after_noop["payload"]["revision"] == before_noop["payload"]["revision"]
    assert after_noop["receipt"]["payload_hash"] == before_noop["receipt"]["payload_hash"]

    context = api.get_boardroom_context("home-fixed")["context"]
    assert context["persistent_truth_source"] == "business_containers"
    assert context["business_identity"]["legal_name"] == "Home Fixed"
    assert context["business_map_projection"]["facts"][-1]["field"] == "monthly_revenue"
    assert context["department_intelligence"]["sales"]["status"] == "operational_foundation_ready"
    assert context["department_intelligence"]["sales"]["runtime_evidence"]["opportunities"] == 1
    assert context["department_intelligence"]["sales"]["runtime_evidence"]["external_authority_claimed"] is False
    assert context["department_intelligence"]["support"]["status"] == "case_authority_foundation_ready"
    assert context["department_intelligence"]["support"]["runtime_evidence"]["cases"] == 1
    assert context["department_intelligence"]["support"]["runtime_evidence"]["automatic_refund_authority_claimed"] is False
    assert context["execution_boundary"]["provider_memory_mutation_allowed"] is False
    assert context["context_hash"].startswith("sha256:")


def test_operational_finance_turn_is_grounded_and_persisted(tmp_path, monkeypatch):
    repository = BusinessContainerRepository(base_dir=tmp_path / "business_containers")
    monkeypatch.setattr(api, "_repo", lambda: repository)
    api.put_finance_model(
        "home-fixed",
        api.ContainerWriteRequest(payload={
            "model_status": "complete",
            "metrics": {
                "gross_margin_percent": {"value": 42.5, "verification": "calculated_from_unverified_input"},
                "monthly_gross_profit": {"value": 1700},
            },
            "missing_information": ["verified bank balance"],
            "discovery_state": {},
        }),
    )
    result = api.finance_agent_turn("home-fixed", api.FinanceAgentTurnRequest(user_text="Show me the margins"))
    assert "42.50%" in result["turn"]["response"]
    assert result["approval_gated"] is True
    saved = repository.load_business_financial_model("home-fixed")
    assert saved.discovery_state["operational_transcript"][0]["user_text"] == "Show me the margins"


def test_operating_model_calculates_stock_procurement_unit_economics_and_board_context(tmp_path, monkeypatch):
    repository = BusinessContainerRepository(base_dir=tmp_path / "business_containers")
    monkeypatch.setattr(api, "_repo", lambda: repository)

    result = api.put_operating_model(
        "home-fixed",
        api.ContainerWriteRequest(
            source="test_products_services",
            payload={
                "currency": "EUR",
                "offerings": [{
                    "name": "Repair day rate", "offering_type": "service",
                    "pricing_basis": "day_rate", "price": 400,
                    "material_cost_per_unit": 50, "labour_cost_per_unit": 160,
                    "expected_monthly_volume": 12,
                }],
                "inventory_items": [{
                    "name": "Roof tiles", "stock_class": "raw_material", "unit": "tiles",
                    "quantity_on_hand": 20, "quantity_reserved": 5, "unit_cost": 3,
                    "reorder_point": 20, "target_stock": 100, "lead_time_days": 4,
                }],
            },
        ),
    )

    model = result["payload"]
    assert model["unit_economics"][0]["contribution_per_unit"] == 190
    assert model["unit_economics"][0]["gross_margin_percent"] == 47.5
    assert model["inventory_metrics"]["total_stock_value"] == 60
    assert model["inventory_metrics"]["reorder_items"] == 1
    assert model["inventory_metrics"]["suggested_procurement_cash_required"] == 255
    assert model["procurement_queue"][0]["requires_approval"] is True

    context = api.get_boardroom_context("home-fixed")["context"]
    assert context["operating_model"]["inventory_metrics"]["total_stock_value"] == 60
    assert context["source_revisions"]["operating_model"] == 1
    facts = context["business_map_projection"]["facts"]
    assert next(item for item in facts if item["field"] == "inventory_metrics")["value"]["reorder_items"] == 1
    ledger = repository.load_department_intelligence("home-fixed")
    assert ledger.departments["procurement"]["operating_model"]["stock_value"] == 60


def test_quoted_job_uses_hr_linked_labour_and_tracks_estimate_against_actual(tmp_path, monkeypatch):
    repository = BusinessContainerRepository(base_dir=tmp_path / "business_containers")
    monkeypatch.setattr(api, "_repo", lambda: repository)
    authority = OrganizationAuthorityService(repository)
    organisation = authority.empty("home-fixed")
    organisation["people"] = [
        {"id": "person.one", "name": "Person One", "email": "one@example.com", "employment_type": "employee", "status": "active", "role_ids": ["role.employee"], "workforce_costing": {"basis": "daily", "base_rate": 120, "productive_hours_month": 160, "hours_per_day": 8}},
        {"id": "person.two", "name": "Person Two", "email": "two@example.com", "employment_type": "contractor", "status": "active", "role_ids": ["role.self_employed_contractor"], "workforce_costing": {"basis": "daily", "base_rate": 100, "productive_hours_month": 160, "hours_per_day": 8}},
    ]
    authority.save("home-fixed", organisation)

    result = api.put_operating_model("home-fixed", api.ContainerWriteRequest(payload={
        "currency": "EUR",
        "offerings": [{"id": "offering.carport", "name": "Quoted installation", "pricing_basis": "quote"}],
        "labour_resources": [
            {"person_id": "person.one", "cost_basis": "daily"},
            {"person_id": "person.two", "cost_basis": "daily"},
        ],
        "jobs": [{"id": "job.carport", "name": "Customer installation", "status": "quote_accepted", "estimated_revenue": 3000, "actual_revenue": 3050}],
        "job_labour_assignments": [
            {"job_id": "job.carport", "person_id": "person.one", "estimated_units": 2, "actual_units": 2},
            {"job_id": "job.carport", "person_id": "person.two", "estimated_units": 2, "actual_units": 2.5},
        ],
        "job_cost_items": [
            {"job_id": "job.carport", "category": "materials", "estimated_cost": 1500, "actual_cost": 1540},
            {"job_id": "job.carport", "category": "travel_fuel", "estimated_cost": 30, "actual_cost": 35},
            {"job_id": "job.carport", "category": "tools_equipment", "estimated_cost": 20, "actual_cost": 30},
        ],
    }))
    model = result["payload"]
    assert [item["cost_rate"] for item in model["labour_resources"]] == [120, 100]
    economics = model["job_economics"][0]
    assert economics["estimated_labour_cost"] == 440
    assert economics["estimated_direct_cost"] == 1990
    assert economics["estimated_contribution"] == 1010
    assert economics["actual_labour_cost"] == 490
    assert economics["actual_direct_cost"] == 2095
    assert economics["actual_contribution"] == 955
    assert economics["cost_variance"] == 105
    facts = api.get_boardroom_context("home-fixed")["context"]["business_map_projection"]["facts"]
    projected_labour = next(item for item in facts if item["field"] == "labour_resources")["value"]
    assert "cost_rate" not in projected_labour[0]
    assert next(item for item in facts if item["field"] == "job_economics")["value"][0]["estimated_contribution"] == 1010
    boardroom_operating = api.get_boardroom_context("home-fixed")["context"]["operating_model"]
    assert "cost_rate" not in boardroom_operating["labour_resources"][0]
    assert boardroom_operating["job_labour_assignments"] == []
    assert boardroom_operating["job_cost_items"] == []
    assert boardroom_operating["governance"]["individual_workforce_costs_redacted"] is True


def test_owner_planning_rate_override_survives_operating_model_save(tmp_path, monkeypatch):
    repository = BusinessContainerRepository(base_dir=tmp_path / "business_containers")
    monkeypatch.setattr(api, "_repo", lambda: repository)
    authority = OrganizationAuthorityService(repository)
    organisation = authority.empty("home-fixed")
    organisation["people"] = [{
        "id": "person.one",
        "name": "Person One",
        "email": "one@example.com",
        "employment_type": "employee",
        "status": "active",
        "role_ids": ["role.employee"],
        "workforce_costing": {
            "basis": "daily", "base_rate": 120,
            "productive_hours_month": 160, "hours_per_day": 8,
        },
    }]
    authority.save("home-fixed", organisation)

    result = api.put_operating_model("home-fixed", api.ContainerWriteRequest(payload={
        "currency": "EUR",
        "labour_resources": [{
            "person_id": "person.one",
            "cost_basis": "daily",
            "cost_rate": 145,
            "rate_source": "manual_planning_override",
        }],
    }))

    resource = result["payload"]["labour_resources"][0]
    assert resource["cost_basis"] == "daily"
    assert resource["cost_rate"] == 145
    assert resource["rate_source"] == "manual_planning_override"
    assert resource["cost_source"] == "owner_planning_override"


@pytest.mark.asyncio
async def test_finance_artifact_writes_bytes_receipt_and_file_cabinet_pointer(tmp_path, monkeypatch):
    runtime_root = tmp_path / "AION_BUSINESS"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", runtime_root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", runtime_root / "business_containers")
    upload = UploadFile(filename="cash flow.xlsx", file=io.BytesIO(b"test spreadsheet bytes"))
    result = await api.upload_finance_artifact("Home_Fixed", category="spreadsheets", file=upload)

    record = result["record"]
    assert result["business_id"] == "home-fixed"
    assert record["storage_state"] == "committed_to_business_container"
    assert record["artifact_hash"].startswith("sha256:")
    assert record["receipt_hash"].startswith("sha256:")
    assert result["file_cabinet_pointer"]["file_cabinet_role"] == "index_pointer_only"

    actual = tmp_path / "AION_BUSINESS" / record["storage_path"]
    assert actual.read_bytes() == b"test spreadsheet bytes"
    assert actual.with_name(f"{record['artifact_id']}.artifact.json").exists()
    cabinet = tmp_path / "AION_BUSINESS" / "workflow_file_cabinets" / "home-fixed" / "tree.json"
    assert "cash flow.xlsx" in cabinet.read_text(encoding="utf-8")
