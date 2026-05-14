# /workspaces/COMDEX/backend/tests/test_aion_equities_openai_company_profile_mapper.py
from __future__ import annotations

from backend.modules.aion_equities.openai_company_profile_mapper import (
    OpenAICompanyProfileMapper,
)


def test_openai_company_profile_mapper_maps_analysis_response():
    mapper = OpenAICompanyProfileMapper()

    out = mapper.map_analysis_to_company_profile(
        company_ref="company/ULVR.L",
        document_ref="document/ULVR.L/2026-Q4-board-pack",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        analysis_response={
            "company_profile": {
                "name": "Unilever PLC",
                "sector": "consumer_staples",
                "country": "GB",
                "description": "Global consumer staples company.",
            },
            "quarter_summary": {
                "headline": "Stable demand with margin improvement.",
                "summary": "Core categories held up well.",
                "key_numbers": {"revenue": 15500, "ebit": 2550},
            },
            "fingerprint": {
                "fingerprint_ref": "company/ULVR.L/fingerprint/core",
                "traits": ["defensive", "cash_generative"],
            },
            "trigger_map": {
                "triggers": [
                    {"id": "fx_watch", "metric": "eur_gbp", "direction": "watch"},
                    {"id": "margin_check", "metric": "ebit_margin", "direction": "up"},
                ]
            },
            "feed_candidates": {
                "feeds": ["fx_rates", "consensus_estimates"],
            },
        },
        generated_by="pytest",
    )

    assert out["company_ref"] == "company/ULVR.L"
    assert out["document_ref"] == "document/ULVR.L/2026-Q4-board-pack"
    assert out["company_profile"]["name"] == "Unilever PLC"
    assert out["quarter_summary"]["key_numbers"]["revenue"] == 15500
    assert out["fingerprint"]["fingerprint_ref"] == "company/ULVR.L/fingerprint/core"
    assert len(out["trigger_map"]["triggers"]) == 2
    assert out["feed_candidates"]["feeds"] == ["fx_rates", "consensus_estimates"]


def test_openai_company_profile_mapper_rejects_non_dict_response():
    mapper = OpenAICompanyProfileMapper()

    try:
        mapper.map_analysis_to_company_profile(
            company_ref="company/ULVR.L",
            document_ref="document/ULVR.L/2026-Q4-board-pack",
            analysis_response=[],  # type: ignore[arg-type]
            generated_by="pytest",
        )
        assert False, "Expected TypeError for non-dict response"
    except TypeError as e:
        assert "analysis_response must be a dict" in str(e)