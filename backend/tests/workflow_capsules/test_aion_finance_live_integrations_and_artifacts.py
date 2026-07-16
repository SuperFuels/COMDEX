from __future__ import annotations

import asyncio
from io import BytesIO
import json
from pathlib import Path

from fastapi import UploadFile

from backend.modules.aion_business.api import business_twin_data_api as data_api
from backend.modules.aion_business.api import finance_integrations_api as xero_api
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


ROOT = Path(__file__).resolve().parents[3]


def configure_runtime(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "AION_BUSINESS"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    monkeypatch.setattr(AIONBusinessPaths, "WORKSPACES", root / "workspaces")
    monkeypatch.setenv("AION_XERO_TOKEN_STORE_DIR", str(tmp_path / "secrets"))


def test_xero_connect_reports_real_configuration_requirements(monkeypatch, tmp_path: Path) -> None:
    configure_runtime(monkeypatch, tmp_path)
    monkeypatch.delenv("XERO_CLIENT_ID", raising=False)
    result = xero_api.xero_connect("Home Fixed")
    assert result["ok"] is False
    assert result["reason"] == "xero_oauth_config_missing"
    assert result["redirect_uri"] == "http://localhost:8080/api/aion/integrations/xero/callback"
    assert result["connection"]["external_writes_enabled"] is False


def test_xero_connect_uses_pkce_and_read_only_granular_scopes(monkeypatch, tmp_path: Path) -> None:
    configure_runtime(monkeypatch, tmp_path)
    monkeypatch.setenv("XERO_CLIENT_ID", "test-client-id")
    result = xero_api.xero_connect("Home Fixed")
    assert result["ok"] is True
    assert "code_challenge=" in result["connect_url"]
    assert "code_challenge_method=S256" in result["connect_url"]
    assert "accounting.invoices.read" in result["connect_url"]
    pending = json.loads((AIONBusinessPaths.business_container_dir("home-fixed") / "integrations/xero/oauth_pending.json").read_text())
    assert pending["code_verifier"]
    assert "access_token" not in pending


def test_xero_read_only_sync_updates_canonical_finance_model(monkeypatch, tmp_path: Path) -> None:
    configure_runtime(monkeypatch, tmp_path)
    business_id = "home-fixed"
    connection = {
        "provider": "xero",
        "business_id": business_id,
        "status": "connected",
        "tenant_id": "tenant-1",
        "tenant_name": "Home Fixed Ltd",
        "read_only": True,
        "external_writes_enabled": False,
    }
    xero_api._write_json(xero_api._connection_path(business_id), connection)

    async def fake_access_token(_business_id: str) -> str:
        return "safe-test-token"

    async def fake_get(_token: str, _tenant: str, path: str, params=None):
        if path == "Organisation":
            return {"Organisations": [{"Name": "Home Fixed Ltd"}]}
        if path == "Accounts":
            return {"Accounts": [{"AccountID": "a1", "Name": "Sales"}]}
        if path == "Invoices":
            return {"Invoices": [{"InvoiceID": "i1", "Status": "AUTHORISED"}]}
        return {"Reports": [{"ReportName": path.split("/")[-1], "Rows": []}]}

    monkeypatch.setattr(xero_api, "_valid_access_token", fake_access_token)
    monkeypatch.setattr(xero_api, "_xero_get", fake_get)
    result = asyncio.run(xero_api.sync_xero(business_id))
    assert result["ok"] is True
    assert result["snapshot"]["summary"]["account_count"] == 1
    assert result["snapshot"]["summary"]["invoice_count"] == 1
    assert result["snapshot"]["read_only"] is True
    assert result["snapshot"]["external_writes_enabled"] is False
    model = json.loads((AIONBusinessPaths.business_container_dir(business_id) / "business_financial_model.json").read_text())
    assert model["integration_evidence"]["xero"]["tenant_name"] == "Home Fixed Ltd"
    assert model["evidence_refs"][0]["verification_status"] == "provider_sourced"


def test_finance_csv_upload_analysis_acceptance_and_file_cabinet(monkeypatch, tmp_path: Path) -> None:
    configure_runtime(monkeypatch, tmp_path)
    upload = UploadFile(
        filename="monthly-finance.csv",
        file=BytesIO(b"month,revenue,costs\nJan,1000,400\nFeb,1200,450\n"),
        headers={"content-type": "text/csv"},
    )
    uploaded = asyncio.run(data_api.upload_finance_artifact("Home Fixed", category="spreadsheets", file=upload))
    artifact_id = uploaded["record"]["artifact_id"]
    assert uploaded["record"]["storage_state"] == "committed_to_business_container"
    assert uploaded["file_cabinet_pointer"]["target"]["category"] == "spreadsheets"

    analysed = data_api.analyse_uploaded_finance_artifact("Home Fixed", artifact_id)
    assert analysed["analysis"]["status"] == "analysed_requires_review"
    assert analysed["analysis"]["tables"][0]["row_count"] == 2
    assert analysed["analysis"]["tables"][0]["numeric_columns"]["revenue"]["sum"] == 2200.0
    assert len(analysed["analysis"]["candidate_facts"]) == 2
    assert analysed["file_cabinet_pointer"]["target"]["analysis_status"] == "analysed_requires_review"

    fact_ids = [item["fact_id"] for item in analysed["analysis"]["candidate_facts"]]
    accepted = data_api.accept_finance_artifact_facts(
        "Home Fixed",
        artifact_id,
        data_api.FinanceArtifactAcceptanceRequest(fact_ids=fact_ids),
    )
    assert accepted["accepted_fact_count"] == 2
    finance_model = json.loads((AIONBusinessPaths.business_container_dir("home-fixed") / "business_financial_model.json").read_text())
    assert finance_model["evidence_refs"][0]["artifact_id"] == artifact_id
    assert finance_model["external_data"]["accepted_artifact_count"] == 1
    assert finance_model["external_data"]["accepted_fact_count"] == 2
    assert len(finance_model["external_data"]["artifacts"][artifact_id]["facts"]) == 2
    listed = data_api.list_finance_artifacts("Home Fixed")
    assert listed["artifacts"][0]["record"]["artifact_id"] == artifact_id
    assert listed["artifacts"][0]["analysis"]["status"] == "accepted_into_finance_model"

    data_api.put_finance_model(
        "Home Fixed",
        data_api.ContainerWriteRequest(payload={"model_status": "discovery_in_progress"}, source="desktop_finance_pilot"),
    )
    finance_model = json.loads((AIONBusinessPaths.business_container_dir("home-fixed") / "business_financial_model.json").read_text())
    assert finance_model["external_data"]["accepted_fact_count"] == 2
    boardroom = data_api.get_boardroom_context("Home Fixed")["context"]
    assert boardroom["function_models"]["finance"]["external_data"]["accepted_fact_count"] == 2
    assert len(boardroom["business_map_projection"]["facts"]) == 2
    assert boardroom["evidence_index"][0]["artifact_id"] == artifact_id
    business_map = json.loads((AIONBusinessPaths.business_container_dir("home-fixed") / "business_map.json").read_text())
    assert {item["verification_status"] for item in business_map["facts"]} == {"accepted_from_source_document"}


def test_finance_analysis_uses_reported_total_without_double_counting() -> None:
    from backend.modules.aion_business.runtime.finance_artifact_analyser import _rows_analysis, _candidate_facts

    table = _rows_analysis([
        ["month", "revenue", "costs"],
        ["Jan", 1000, 400],
        ["Feb", 1200, 450],
        ["Total", 2200, 850],
    ], "Monthly_Data")
    assert table["numeric_columns"]["revenue"]["sum"] == 2200.0
    assert table["reported_totals"]["revenue"] == 2200.0
    facts = _candidate_facts([table])
    revenue = next(item for item in facts if item["source_column"] == "revenue")
    assert revenue["value"] == 2200.0
    assert revenue["aggregation"] == "reported_total_row"


def test_finance_analysis_does_not_promote_decorative_report_title_column() -> None:
    from backend.modules.aion_business.runtime.finance_artifact_analyser import _rows_analysis, _candidate_facts

    table = _rows_analysis([
        ["Profit and Loss Statement", "January", "February"],
        ["Revenue", 1000, 1200],
        ["Costs", 400, 450],
    ], "Profit_and_Loss")
    assert not any(item["source_column"] == "profit_and_loss_statement" for item in _candidate_facts([table]))


def test_operating_model_catalogue_and_inventory_imports_are_persisted_and_indexed(monkeypatch, tmp_path: Path) -> None:
    configure_runtime(monkeypatch, tmp_path)
    catalogue = UploadFile(
        filename="rate-card.csv",
        file=BytesIO(b"name,type,charge_basis,price,unit,monthly_volume,material_cost\nPlumber day,service,day_rate,420,day,10,35\n"),
        headers={"content-type": "text/csv"},
    )
    imported_catalogue = asyncio.run(data_api.import_operating_model_spreadsheet("Home Fixed", category="offerings", file=catalogue))
    assert imported_catalogue["import"]["imported_row_count"] == 1
    assert imported_catalogue["payload"]["unit_economics"][0]["contribution_per_unit"] == 385

    stock = UploadFile(
        filename="stock.csv",
        file=BytesIO(b"item,type,on_hand,reserved,unit_cost,min_stock,max_stock,lead_time\nRoof tile,raw_material,10,2,3,10,50,4\n"),
        headers={"content-type": "text/csv"},
    )
    imported_stock = asyncio.run(data_api.import_operating_model_spreadsheet("Home Fixed", category="inventory", file=stock))
    assert imported_stock["payload"]["inventory_metrics"]["total_stock_value"] == 30
    assert imported_stock["payload"]["inventory_metrics"]["suggested_procurement_cash_required"] == 126
    assert imported_stock["file_cabinet_pointer"]["target"]["category"] == "inventory"
    cabinet = (AIONBusinessPaths.ROOT / "workflow_file_cabinets" / "home-fixed" / "tree.json").read_text(encoding="utf-8")
    assert "Products & Services" in cabinet
    assert "rate-card.csv" in cabinet
    assert "stock.csv" in cabinet


def test_finance_pdf_analysis_preserves_text_as_reviewable_evidence(monkeypatch, tmp_path: Path) -> None:
    configure_runtime(monkeypatch, tmp_path)
    from pypdf import PdfWriter

    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buffer)
    upload = UploadFile(filename="statement.pdf", file=BytesIO(buffer.getvalue()), headers={"content-type": "application/pdf"})
    uploaded = asyncio.run(data_api.upload_finance_artifact("Home Fixed", category="bank-statements", file=upload))
    analysed = data_api.analyse_uploaded_finance_artifact("Home Fixed", uploaded["record"]["artifact_id"])
    assert analysed["analysis"]["document"]["page_count"] == 1
    assert analysed["analysis"]["acceptance_required"] is True
    assert analysed["analysis"]["warnings"]


def test_desktop_finance_surface_exposes_live_xero_and_reviewed_artifact_actions() -> None:
    pilot = (ROOT / "desktop/mac/src/aion_finance_pilot.js").read_text(encoding="utf-8")
    client = (ROOT / "desktop/mac/src/aion_business_container_client.js").read_text(encoding="utf-8")
    preload = (ROOT / "desktop/mac/electron/preload.js").read_text(encoding="utf-8")
    assert "data-aion-xero-connect" in pilot
    assert "data-aion-xero-sync" in pilot
    assert "data-aion-finance-analyse-artifact" in pilot
    assert "data-aion-finance-accept-artifact" in pilot
    assert "data-aion-finance-accept-all-artifacts" in pilot
    assert "data-aion-finance-fact-value" in pilot
    assert "data-aion-finance-review-evidence" in pilot
    assert "evidenceReviewState" in pilot
    assert "applyEvidenceAnswers" in pilot
    assert "reconcileFinanceArtifacts" in pilot
    assert "compactStateForLocalStorage" in pilot
    assert "listFinanceArtifacts" in client
    assert "data-aion-finance-voice-answer" in pilot
    assert "data-aion-finance-hear-question" in pilot
    assert "/api/aion/voice/stt" in pilot
    assert "playLocalVoice" in pilot
    assert "requestMicrophonePermission" in pilot
    assert "connectXero" in client and "syncXero" in client
    assert "analyseFinanceArtifact" in client and "acceptFinanceArtifactFacts" in client
    assert "openExternalUrl" in preload


def test_commerce_sources_are_sales_owned_with_a_finance_projection() -> None:
    schema = (ROOT / "desktop/mac/src/aion_commerce_source_schema.js").read_text(encoding="utf-8")
    assert "system_owner: 'sales'" in schema
    assert "finance_receives_normalised_projection: true" in schema
    assert "finance_does_not_duplicate_provider_connection: true" in schema
    for provider in ["shopify", "magento", "square"]:
        assert provider in schema
