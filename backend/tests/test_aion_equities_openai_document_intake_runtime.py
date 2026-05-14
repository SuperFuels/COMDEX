from __future__ import annotations

from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.openai_company_profile_mapper import (
    OpenAICompanyProfileMapper,
)
from backend.modules.aion_equities.openai_document_analysis_runtime import (
    OpenAIDocumentAnalysisRuntime,
)
from backend.modules.aion_equities.openai_document_intake_runtime import (
    OpenAIDocumentIntakeRuntime,
)
from backend.modules.aion_equities.openai_operating_brief_store import (
    OpenAIOperatingBriefStore,
)
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.variable_watch_store import VariableWatchStore


def test_openai_document_intake_runtime_returns_consolidated_artifact(tmp_path):
    brief_store = OpenAIOperatingBriefStore(base_dir=tmp_path)
    saved = brief_store.save_operating_brief(
        brief_id="brief/aion_equities_default",
        version="v1",
        title="AION Equities",
        summary="Operating brief",
        sections=[{"title": "Role", "content": "Analyze company documents"}],
    )
    brief_store.set_active_brief(saved["brief_id"])

    def fake_openai_client(packet):
        assert packet["packet_type"] == "openai_document_analysis"
        return {
            "company_profile": {
                "name": "Ashtead Group",
                "sector": "plant_hire",
                "country": "UK",
                "description": "Equipment rental business",
            },
            "quarter_summary": {
                "headline": "Good quarter",
                "summary": "Rental demand remained resilient",
                "key_numbers": {"revenue_growth_pct": 8.2},
                "fiscal_period": "2026-Q1",
            },
            "fingerprint": {
                "fingerprint_ref": "fingerprint/AHT.L/core",
                "traits": ["predictable", "asset_heavy"],
            },
            "trigger_map": {
                "triggers": [
                    {
                        "trigger_id": "utilisation_up",
                        "variable_name": "fleet_utilisation",
                        "data_source": "feed/fleet_utilisation",
                        "impact_direction": "positive",
                        "impact_weight": 0.7,
                        "confidence": 80,
                        "thesis_action": "increase_conviction",
                    }
                ]
            },
            "feed_candidates": {
                "feeds": [{"feed_id": "feed/us_construction_activity", "kind": "macro"}]
            },
            "assessment_seed": {
                "acs_band": "high",
                "sector_confidence_tier": "high",
            },
            "thesis_seed": {
                "mode": "long",
                "summary": "Stable rental demand with quality execution",
            },
            "variable_watch_seed": {
                "variables": ["fleet_utilisation", "rental_rate_growth"]
            },
            "quarter_event": {
                "fiscal_period": "2026-Q1",
                "published_at": "2026-06-18",
                "headline": "Q1 update",
                "summary": "Trading in line",
                "key_numbers": {"revenue_growth_pct": 8.2},
            },
        }

    analysis_runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=fake_openai_client,
    )
    mapper = OpenAICompanyProfileMapper()
    quarter_event_store = QuarterEventStore(base_dir=tmp_path)
    trigger_map_store = CompanyTriggerMapStore(base_dir=tmp_path)
    variable_watch_store = VariableWatchStore(base_dir=tmp_path)

    runtime = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=mapper,
        quarter_event_store=quarter_event_store,
        company_trigger_map_store=trigger_map_store,
        variable_watch_store=variable_watch_store,
    )

    out = runtime.run_document_intake(
        company_ref="company/AHT.L",
        document_ref="document/AHT.L/2026-Q1",
        document_text="Quarterly board pack extracted text",
        document_type="board_pack",
        thesis_ref="thesis/AHT.L/long/2026Q2_pre_earnings",
    )

    # Quarter event persisted
    assert out["persisted_objects"]["quarter_event_ref"] == "quarter_event/company/AHT.L/2026-Q1"
    loaded_qe = quarter_event_store.load_quarter_event("quarter_event/company/AHT.L/2026-Q1")
    assert loaded_qe["headline"] == "Q1 update"

    # Trigger map persisted
    assert out["persisted_objects"]["trigger_map_ref"] == "company/AHT.L/trigger_map/2026-Q1"
    loaded_tm = trigger_map_store.load_company_trigger_map("company/AHT.L", "2026-Q1", validate=False)
    assert loaded_tm["company_trigger_map_id"] == "company/AHT.L/trigger_map/2026-Q1"

    # Variable watch persisted
    assert out["persisted_objects"]["variable_watch_ref"] == "company/AHT.L/variable_watch/2026-Q1"
    loaded_vw = variable_watch_store.load_variable_watch("company/AHT.L", "2026-Q1")
    assert loaded_vw["variables"] == ["fleet_utilisation", "rental_rate_growth"]


def test_openai_document_intake_runtime_intake_document_alias_works(tmp_path):
    brief_store = OpenAIOperatingBriefStore(base_dir=tmp_path)
    saved = brief_store.save_operating_brief(
        brief_id="brief/aion_equities_default",
        version="v1",
        title="AION Equities",
        summary="Operating brief",
        brief_text="Analyze company documents and return structured output.",
    )
    brief_store.set_active_brief(saved["brief_id"])

    def fake_openai_client(packet):
        return {
            "profile": {
                "name": "Tesco",
                "sector": "consumer_staples",
                "country": "UK",
                "description": "Retailer",
            },
            "quarter": {
                "headline": "Stable quarter",
                "summary": "Defensive trading held up",
                "key_numbers": {"like_for_like_sales_pct": 3.1},
                "fiscal_period": "2026-Q1",
            },
            "triggers": [
                {
                    "trigger_id": "volume_trend",
                    "variable_name": "volume_growth",
                    "data_source": "feed/uk_consumer_spend",
                    "impact_direction": "positive",
                }
            ],
            "watchlist": {"variables": ["volume_growth"]},
        }

    analysis_runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=fake_openai_client,
    )
    mapper = OpenAICompanyProfileMapper()
    quarter_event_store = QuarterEventStore(base_dir=tmp_path)
    trigger_map_store = CompanyTriggerMapStore(base_dir=tmp_path)
    variable_watch_store = VariableWatchStore(base_dir=tmp_path)

    runtime = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=mapper,
        quarter_event_store=quarter_event_store,
        company_trigger_map_store=trigger_map_store,
        variable_watch_store=variable_watch_store,
    )

    out = runtime.intake_document(
        company_ref="company/TSCO.L",
        document_ref="document/TSCO.L/2026-Q1",
        document_text="Extracted text",
    )

    assert out["persisted_objects"]["quarter_event_ref"] == "quarter_event/company/TSCO.L/2026-Q1"
    assert out["persisted_objects"]["trigger_map_ref"] == "company/TSCO.L/trigger_map/2026-Q1"

    # Variable watch persisted (alias watchlist)
    assert out["persisted_objects"]["variable_watch_ref"] == "company/TSCO.L/variable_watch/2026-Q1"
    loaded_vw = variable_watch_store.load_variable_watch("company/TSCO.L", "2026-Q1")
    assert loaded_vw["variables"] == ["volume_growth"]