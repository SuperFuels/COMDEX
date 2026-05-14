from __future__ import annotations

from backend.modules.aion_equities.assessment_runtime import AssessmentRuntime
from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.openai_company_profile_mapper import OpenAICompanyProfileMapper
from backend.modules.aion_equities.openai_document_analysis_runtime import OpenAIDocumentAnalysisRuntime
from backend.modules.aion_equities.openai_document_intake_runtime import OpenAIDocumentIntakeRuntime
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.thesis_runtime import ThesisRuntime
from backend.modules.aion_equities.thesis_store import ThesisStore


def test_openai_document_intake_persists_assessment_and_thesis(tmp_path):
    brief_store = OpenAIOperatingBriefStore(base_dir=tmp_path)
    saved_brief = brief_store.save_operating_brief(
        brief_id="brief/aion_equities_default",
        version="v1",
        title="AION Equities",
        summary="Operating brief",
        sections=[{"title": "Role", "content": "Analyze company documents"}],
    )
    brief_store.set_active_brief(saved_brief["brief_id"])

    # Seed company (minimal fields used by AssessmentRuntime)
    seed_store = PilotCompanySeedStore(base_dir=tmp_path)
    seed_store.save_company_seed(
        company_ref="company/AHT.L",
        company_id="company/AHT.L",
        ticker="AHT.L",
        name="Ashtead",
        sector="plant_hire",
        country="UK",
        predictability_profile={"acs_band": "high", "sector_confidence_tier": "tier_1"},
    )

    def fake_openai_client(packet):
        return {
            "company_profile": {"name": "Ashtead", "sector": "plant_hire", "country": "UK"},
            "quarter_summary": {
                "headline": "Good quarter",
                "summary": "Resilient demand",
                "key_numbers": {"revenue": 1000.0, "ebit": 120.0, "free_cash_flow": 80.0, "net_debt": 2000.0},
                "fiscal_period": "2026-Q1",
            },
            "trigger_map": {"triggers": [{"trigger_id": "util", "variable_name": "utilisation"}]},
            "thesis_seed": {"mode": "long", "window": "medium_term"},
            "quarter_event": {
                "fiscal_period": "2026-Q1",
                "published_at": "2026-06-18",
                "headline": "Q1 update",
                "summary": "Trading in line",
                "key_numbers": {"revenue": 1000.0, "ebit": 120.0, "free_cash_flow": 80.0, "net_debt": 2000.0},
            },
        }

    analysis_runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=fake_openai_client,
    )

    mapper = OpenAICompanyProfileMapper()
    qe_store = QuarterEventStore(base_dir=tmp_path)
    tm_store = CompanyTriggerMapStore(base_dir=tmp_path)

    assessment_runtime = AssessmentRuntime(
        pilot_company_seed_store=seed_store,
        quarter_event_store=qe_store,
    )
    assessment_store = AssessmentStore(base_dir=tmp_path)

    thesis_store = ThesisStore(base_dir=tmp_path)
    thesis_runtime = ThesisRuntime(
        pilot_company_seed_store=seed_store,
    )

    runtime = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=mapper,
        quarter_event_store=qe_store,
        company_trigger_map_store=tm_store,
        assessment_runtime=assessment_runtime,
        assessment_store=assessment_store,
        thesis_runtime=thesis_runtime,
        thesis_store=thesis_store,
    )

    out = runtime.run_document_intake(
        company_ref="company/AHT.L",
        document_ref="document/AHT.L/2026-Q1",
        document_text="Extracted text",
        thesis_ref="thesis/AHT.L/long/medium_term",
    )

    assert out["persisted_objects"]["quarter_event_ref"] == "quarter_event/company/AHT.L/2026-Q1"
    assert out["persisted_objects"]["trigger_map_ref"] == "company/AHT.L/trigger_map/2026-Q1"

    # Assessment created and stored
    assert isinstance(out["persisted_objects"].get("assessment_ref"), str)
    latest_assessment = assessment_store.load_latest_assessment("company/AHT.L")
    assert latest_assessment["assessment_id"] == out["persisted_objects"]["assessment_ref"]

    # Thesis created and stored
    assert isinstance(out["persisted_objects"].get("thesis_ref"), str)
    latest_thesis = thesis_store.load_latest_thesis_state(out["persisted_objects"]["thesis_ref"])
    assert latest_thesis["thesis_id"] == out["persisted_objects"]["thesis_ref"]