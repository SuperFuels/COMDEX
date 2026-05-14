from __future__ import annotations

from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.document_ingestion_runtime import DocumentIngestionRuntime
from backend.modules.aion_equities.source_document_store import SourceDocumentStore


def test_document_ingestion_runtime_registers_source_document(tmp_path):
    source_store = SourceDocumentStore(tmp_path)
    runtime = DocumentIngestionRuntime(source_document_store=source_store)

    out = runtime.register_source_document(
        company_ref="company/PAGE.L",
        source_type="quarterly_report",
        fiscal_period_ref="2026Q1",
        source_file_ref="files/page_q1.pdf",
        parsed_text_ref="parsed/page_q1.txt",
        tables_ref="tables/page_q1.json",
        provenance_hash="sha256:abc",
    )

    assert out["company_ref"] == "company/PAGE.L"
    assert out["source_type"] == "quarterly_report"
    assert out["fiscal_period_ref"] == "2026Q1"
    assert out["ingestion_status"] == "registered"


def test_document_ingestion_runtime_builds_quarter_event_and_assessment_input(tmp_path):
    source_store = SourceDocumentStore(tmp_path)
    runtime = DocumentIngestionRuntime(source_document_store=source_store)

    out = runtime.ingest_document(
        company_ref="company/PAGE.L",
        source_type="trading_update",
        fiscal_period_ref="2026Q1",
        source_file_ref="files/page_update.pdf",
        narrative_summary={"headline": "France weak, US stable"},
        structured_financials={"gross_profit_change_pct": -3.2},
    )

    assert out["source_document"]["ingestion_status"] == "mapped"
    assert out["quarter_event_payload"]["company_ref"] == "company/PAGE.L"
    assert out["quarter_event_payload"]["fiscal_period_ref"] == "2026Q1"
    assert out["assessment_input_payload"]["source_document_ref"] == out["source_document"]["document_id"]
    assert out["assessment_input_payload"]["structured_financials"]["gross_profit_change_pct"] == -3.2


def test_document_ingestion_runtime_can_create_trigger_map_payload(tmp_path):
    source_store = SourceDocumentStore(tmp_path)
    trigger_store = CompanyTriggerMapStore(tmp_path)
    runtime = DocumentIngestionRuntime(
        source_document_store=source_store,
        trigger_map_store=trigger_store,
    )

    out = runtime.ingest_document(
        company_ref="company/ULVR.L",
        source_type="quarterly_report",
        fiscal_period_ref="2026Q4",
        source_file_ref="files/ulvr_q4.pdf",
        trigger_entries=[
            {
                "trigger_id": "eurusd_fx",
                "variable_name": "EURUSD",
                "data_source": "EURUSD",
                "current_state": "inactive",
                "threshold_rule": "manual",
                "lag_expectation": "0d",
                "impact_direction": "positive",
                "impact_weight": 0.4,
                "confidence": 70.0,
                "thesis_action": "refresh_pre_earnings",
            }
        ],
    )

    trig = out["trigger_map_payload"]
    assert trig is not None
    assert trig["company_ref"] == "company/ULVR.L"
    assert trig["fiscal_period_ref"] == "2026Q4"


def test_document_ingestion_runtime_links_source_document_to_trigger_map(tmp_path):
    source_store = SourceDocumentStore(tmp_path)
    trigger_store = CompanyTriggerMapStore(tmp_path)
    runtime = DocumentIngestionRuntime(
        source_document_store=source_store,
        trigger_map_store=trigger_store,
    )

    out = runtime.ingest_document(
        company_ref="company/ULVR.L",
        source_type="board_pack",
        fiscal_period_ref="2026Q4",
        source_file_ref="files/ulvr_board_pack.pdf",
    )

    linked_refs = out["source_document"].get("linked_refs", {})
    assert linked_refs["quarter_event_ref"] == "company/ULVR.L/quarter_event/2026Q4"
    assert linked_refs["trigger_map_ref"] == "company/ULVR.L/trigger_map/2026Q4"