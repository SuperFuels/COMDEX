from __future__ import annotations

from backend.modules.aion_equities.assessment_runtime import AssessmentRuntime
from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.company_intelligence_snapshot_loader import CompanyIntelligenceSnapshotLoader
from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.document_ingestion_runtime import DocumentIngestionRuntime
from backend.modules.aion_equities.openai_company_profile_mapper import OpenAICompanyProfileMapper
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_document_analysis_runtime import OpenAIDocumentAnalysisRuntime
from backend.modules.aion_equities.openai_document_intake_runtime import OpenAIDocumentIntakeRuntime
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.reference_maintenance_runtime import ReferenceMaintenanceRuntime
from backend.modules.aion_equities.source_document_store import SourceDocumentStore
from backend.modules.aion_equities.thesis_runtime import ThesisRuntime
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.variable_watch_store import VariableWatchStore


def test_document_ingestion_to_intake_bridge_end_to_end(tmp_path):
    # ---- stores / seed ----
    brief_store = OpenAIOperatingBriefStore(base_dir=tmp_path)
    brief = brief_store.save_operating_brief(
        brief_id="brief/aion_equities_default",
        version="v1",
        title="AION Equities",
        summary="Operating brief",
        sections=[{"title": "Role", "content": "Analyze docs"}],
    )
    brief_store.set_active_brief(brief["brief_id"])

    seed_store = PilotCompanySeedStore(base_dir=tmp_path)
    seed_store.save_company_seed(
        company_ref="company/PAGE.L",
        company_id="company/PAGE.L",
        ticker="PAGE.L",
        name="PageGroup",
        sector="staffing",
        country="UK",
        predictability_profile={"acs_band": "high", "sector_confidence_tier": "tier_1"},
    )

    source_store = SourceDocumentStore(tmp_path)
    qe_store = QuarterEventStore(base_dir=tmp_path)
    tm_store = CompanyTriggerMapStore(base_dir=tmp_path)
    vw_store = VariableWatchStore(base_dir=tmp_path)
    assessment_store = AssessmentStore(base_dir=tmp_path)
    thesis_store = ThesisStore(base_dir=tmp_path)

    # ---- ingestion runtime (registers + links) ----
    ingestion = DocumentIngestionRuntime(
        source_document_store=source_store,
        trigger_map_store=tm_store,
    )

    ingest_out = ingestion.ingest_document(
        company_ref="company/PAGE.L",
        source_type="quarterly_report",
        fiscal_period_ref="2026-Q1",
        source_file_ref="files/page_q1.pdf",
        parsed_text_ref="parsed/page_q1.txt",
        narrative_summary={"headline": "France weak, US stable", "summary": "Mixed demand"},
        structured_financials={"revenue": 1000.0, "ebit": 80.0, "free_cash_flow": 60.0, "net_debt": 500.0},
        trigger_entries=[{"trigger_id": "fx", "variable_name": "EURGBP", "data_source": "feed/EURGBP"}],
    )

    # ---- OpenAI doc analysis runtime ----
    def fake_openai_client(packet):
        # Packet contains document.text; in the real flow you'd load parsed_text_ref content.
        return {
            "company_profile": {"name": "PageGroup", "sector": "staffing", "country": "UK"},
            "quarter_summary": {
                "headline": "Mixed quarter",
                "summary": "France weak, US stable",
                "key_numbers": {"revenue": 1000.0, "ebit": 80.0, "free_cash_flow": 60.0, "net_debt": 500.0},
                "fiscal_period": "2026-Q1",
            },
            "trigger_map": {
                "triggers": [
                    {"trigger_id": "fx", "variable_name": "EURGBP", "data_source": "feed/EURGBP"}
                ]
            },
            "variable_watch_seed": {"variables": ["EURGBP", "gross_margin"]},
            "thesis_seed": {"mode": "long", "window": "medium_term"},
            "quarter_event": {
                "fiscal_period": "2026-Q1",
                "published_at": "2026-06-18",
                "headline": "Q1 update",
                "summary": "Mixed demand",
                "key_numbers": {"revenue": 1000.0, "ebit": 80.0, "free_cash_flow": 60.0, "net_debt": 500.0},
            },
        }

    analysis_runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=fake_openai_client,
    )

    mapper = OpenAICompanyProfileMapper()
    assessment_runtime = AssessmentRuntime(pilot_company_seed_store=seed_store, quarter_event_store=qe_store)
    thesis_runtime = ThesisRuntime(pilot_company_seed_store=seed_store)
    ref_runtime = ReferenceMaintenanceRuntime(pilot_company_seed_store=seed_store)

    intake = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=mapper,
        quarter_event_store=qe_store,
        company_trigger_map_store=tm_store,
        variable_watch_store=vw_store,
        assessment_runtime=assessment_runtime,
        assessment_store=assessment_store,
        thesis_runtime=thesis_runtime,
        thesis_store=thesis_store,
        reference_maintenance_runtime=ref_runtime,
    )

    # NOTE: for now we pass "document_text" directly.
    # Later we’ll implement real parsed_text_ref loading.
    intake_out = intake.run_document_intake(
        company_ref="company/PAGE.L",
        document_ref=ingest_out["source_document"]["document_id"],
        document_text="extracted pdf text placeholder",
        document_type="quarterly_report",
    )

    assert intake_out["persisted_objects"]["quarter_event_ref"] == "quarter_event/company/PAGE.L/2026-Q1"
    assert intake_out["persisted_objects"]["trigger_map_ref"] == "company/PAGE.L/trigger_map/2026-Q1"
    assert intake_out["persisted_objects"]["variable_watch_ref"] == "company/PAGE.L/variable_watch/2026-Q1"
    assert isinstance(intake_out["persisted_objects"]["assessment_ref"], str)
    assert isinstance(intake_out["persisted_objects"]["thesis_ref"], str)

    # Company refs updated
    company = seed_store.load_company_seed("company/PAGE.L")
    assert company["latest_assessment_ref"] == intake_out["persisted_objects"]["assessment_ref"]
    assert intake_out["persisted_objects"]["quarter_event_ref"] in company["quarter_event_refs"]
    assert intake_out["persisted_objects"]["trigger_map_ref"] in company["trigger_map_refs"]
    assert intake_out["persisted_objects"]["variable_watch_ref"] in company["variable_watch_refs"]

    # Bonus: snapshot loader works on the resulting state
    loader = CompanyIntelligenceSnapshotLoader(
        pilot_company_seed_store=seed_store,
        assessment_store=assessment_store,
        thesis_store=thesis_store,
        quarter_event_store=qe_store,
        trigger_map_store=tm_store,
        variable_watch_store=vw_store,
    )
    snap = loader.load_snapshot(company_ref="company/PAGE.L")
    assert snap["assessment"] is not None
    assert snap["trigger_map"] is not None
    assert snap["variable_watch"] is not None

    # Bonus: context packet builder can auto-load snapshot
    ctx_builder = OpenAIContextPacketBuilder(
        operating_brief_store=brief_store,
        company_snapshot_loader=loader,
    )
    pkt = ctx_builder.build_context_packet(
        company_ref="company/PAGE.L",
        proposal_id="proposal/test",
        review_id="review/test",
        requested_action="review_trade",
        proposal_packet={"proposal_id": "proposal/test", "requested_action": "review_trade"},
    )
    assert pkt["company_intelligence_pack"]["company_ref"] == "company/PAGE.L"