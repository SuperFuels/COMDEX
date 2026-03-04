# /workspaces/COMDEX/backend/tests/test_aion_equities_openai_document_intake_runtime.py
from __future__ import annotations

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
                        "impact_direction": "positive",
                    }
                ]
            },
            "feed_candidates": {
                "feeds": [
                    {"feed_id": "feed/us_construction_activity", "kind": "macro"}
                ]
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
    runtime = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=mapper,
    )

    out = runtime.run_document_intake(
        company_ref="company/AHT.L",
        document_ref="document/AHT.L/2026-Q1",
        document_text="Quarterly board pack extracted text",
        document_type="board_pack",
        thesis_ref="thesis/AHT.L/long/2026Q2_pre_earnings",
    )

    assert out["company_ref"] == "company/AHT.L"
    assert out["document_ref"] == "document/AHT.L/2026-Q1"
    assert out["document_type"] == "board_pack"
    assert out["thesis_ref"] == "thesis/AHT.L/long/2026Q2_pre_earnings"

    assert out["normalized_analysis"]["company_profile"]["name"] == "Ashtead Group"
    assert out["mapped_objects"]["company_profile"]["name"] == "Ashtead Group"
    assert out["mapped_objects"]["quarter_event"]["fiscal_period"] == "2026-Q1"
    assert out["mapped_objects"]["assessment_seed"]["payload"]["acs_band"] == "high"
    assert out["mapped_objects"]["thesis_seed"]["payload"]["mode"] == "long"
    assert out["mapped_objects"]["variable_watch_seed"]["payload"]["variables"] == [
        "fleet_utilisation",
        "rental_rate_growth",
    ]


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
            },
            "triggers": [
                {"trigger_id": "volume_trend", "variable_name": "volume_growth"}
            ],
            "feeds": [
                {"feed_id": "feed/uk_consumer_spend", "kind": "macro"}
            ],
            "assessment": {"acs_band": "medium_high"},
            "thesis": {"mode": "long"},
            "watchlist": {"variables": ["volume_growth"]},
        }

    analysis_runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=fake_openai_client,
    )
    mapper = OpenAICompanyProfileMapper()
    runtime = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=mapper,
    )

    out = runtime.intake_document(
        company_ref="company/TSCO.L",
        document_ref="document/TSCO.L/2026-Q1",
        document_text="Extracted text",
    )

    assert out["normalized_analysis"]["company_profile"]["name"] == "Tesco"
    assert out["mapped_objects"]["company_profile"]["sector"] == "consumer_staples"
    assert out["mapped_objects"]["trigger_map"]["triggers"][0]["trigger_id"] == "volume_trend"
    assert out["mapped_objects"]["feed_candidates"]["feeds"][0]["feed_id"] == "feed/uk_consumer_spend"
    assert out["mapped_objects"]["assessment_seed"]["payload"]["acs_band"] == "medium_high"
    assert out["mapped_objects"]["thesis_seed"]["payload"]["mode"] == "long"