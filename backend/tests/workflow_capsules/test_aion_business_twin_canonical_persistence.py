import io
from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from backend.modules.aion_business.api import business_twin_data_api as api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


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

    appended = api.append_business_map_facts(
        "home-fixed",
        api.BusinessMapFactsRequest(
            source="finance_pilot_test",
            facts=[{"function": "finance", "field": "monthly_revenue", "value": 4200, "source_ref": "turn_1"}],
        ),
    )
    assert appended["appended"] == 1
    assert api.append_business_map_facts(
        "home-fixed",
        api.BusinessMapFactsRequest(
            source="finance_pilot_test",
            facts=[{"function": "finance", "field": "monthly_revenue", "value": 4200, "source_ref": "turn_1"}],
        ),
    )["appended"] == 0

    context = api.get_boardroom_context("home-fixed")["context"]
    assert context["persistent_truth_source"] == "business_containers"
    assert context["business_identity"]["legal_name"] == "Home Fixed"
    assert context["business_map_projection"]["facts"][-1]["field"] == "monthly_revenue"
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
