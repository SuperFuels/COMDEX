from __future__ import annotations

from backend.modules.aion_equities.aion_equities_sqi_container_writer import (
    AIONEquitiesSQIContainerWriter,
)


def test_sqi_writer_builds_company_container():
    writer = AIONEquitiesSQIContainerWriter()

    company = {
        "company_id": "company/ULVR.L",
        "ticker": "ULVR.L",
        "name": "Unilever PLC",
        "predictability_profile": {
            "acs_band": "high",
            "sector_confidence_tier": "tier_1",
        },
    }

    out = writer.write_company(
        company,
        assessment_ref="assessment/company/ULVR.L/2026-03-01",
        thesis_refs=["thesis/ULVR.L/long/medium_term"],
        trigger_map_ref="company/ULVR.L/trigger_map/2026Q1",
    )

    assert out["meta"]["sqi_ready"] is True
    assert out["meta"]["source_ref"] == "company/ULVR.L"
    assert out["runtime_context"]["kg_node_ref"] == "company/ULVR.L"
    assert out["sqi_context"]["object_type"] == "company"
    assert out["sqi_context"]["coherence"]["status"] in {"medium", "high"}
    assert out["sqi_context"]["runtime_refs"]["trigger_map_ref"] == "company/ULVR.L/trigger_map/2026Q1"


def test_sqi_writer_builds_assessment_container():
    writer = AIONEquitiesSQIContainerWriter()

    assessment = {
        "assessment_id": "assessment/company/ULVR.L/2026-03-01",
        "entity_id": "company/ULVR.L",
        "scores": {
            "business_quality_score": 82.0,
            "analytical_confidence_score": 78.0,
            "automation_opportunity_score": 60.0,
        },
    }

    out = writer.write_assessment(
        assessment,
        company_ref="company/ULVR.L",
        thesis_ref="thesis/ULVR.L/long/medium_term",
    )

    assert out["meta"]["sqi_ready"] is True
    assert out["sqi_context"]["object_type"] == "assessment"
    assert out["sqi_context"]["coherence"]["score"] > 0.0
    assert out["sqi_context"]["runtime_refs"]["company_ref"] == "company/ULVR.L"
    assert out["sqi_context"]["runtime_refs"]["thesis_ref"] == "thesis/ULVR.L/long/medium_term"


def test_sqi_writer_builds_thesis_and_trigger_map_containers():
    writer = AIONEquitiesSQIContainerWriter()

    thesis = {
        "thesis_id": "thesis/ULVR.L/long/medium_term",
        "ticker": "ULVR.L",
        "mode": "long",
        "status": "active",
        "assessment_refs": ["assessment/company/ULVR.L/2026-03-01"],
    }

    thesis_out = writer.write_thesis(
        thesis,
        company_ref="company/ULVR.L",
        trigger_map_ref="company/ULVR.L/trigger_map/2026Q1",
    )

    assert thesis_out["meta"]["sqi_ready"] is True
    assert thesis_out["sqi_context"]["object_type"] == "thesis"
    assert thesis_out["sqi_context"]["runtime_refs"]["company_ref"] == "company/ULVR.L"

    trigger_map = {
        "company_trigger_map_id": "company/ULVR.L/trigger_map/2026Q1",
        "company_ref": "company/ULVR.L",
        "summary": {
            "active_trigger_count": 2,
            "confirmed_trigger_count": 1,
            "broken_trigger_count": 0,
        },
        "triggers": [
            {
                "trigger_id": "eurusd_fx",
                "current_state": "confirmed",
            }
        ],
    }

    trigger_out = writer.write_trigger_map(
        trigger_map,
        company_ref="company/ULVR.L",
        thesis_ref="thesis/ULVR.L/long/medium_term",
    )

    assert trigger_out["meta"]["sqi_ready"] is True
    assert trigger_out["sqi_context"]["object_type"] == "trigger_map"
    assert trigger_out["sqi_context"]["coherence"]["score"] >= 0.55
    assert trigger_out["sqi_context"]["runtime_refs"]["thesis_ref"] == "thesis/ULVR.L/long/medium_term"


def test_sqi_writer_builds_pre_earnings_estimate_container():
    writer = AIONEquitiesSQIContainerWriter()

    estimate = {
        "pre_earnings_estimate_id": "company/ULVR.L/pre_earnings/2026-Q1",
        "company_ref": "company/ULVR.L",
        "divergence": {
            "divergence_score": 34.0,
            "confidence": 76.0,
        },
        "signal": {
            "catalyst_strength": 68.0,
            "long_candidate": True,
            "short_candidate": False,
        },
    }

    out = writer.write_pre_earnings_estimate(
        estimate,
        company_ref="company/ULVR.L",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        trigger_map_ref="company/ULVR.L/trigger_map/2026Q1",
    )

    assert out["meta"]["sqi_ready"] is True
    assert out["sqi_context"]["object_type"] == "pre_earnings_estimate"
    assert out["sqi_context"]["runtime_refs"]["company_ref"] == "company/ULVR.L"
    assert out["sqi_context"]["runtime_refs"]["trigger_map_ref"] == "company/ULVR.L/trigger_map/2026Q1"
    assert out["runtime_context"]["source_ref"] == "company/ULVR.L/pre_earnings/2026-Q1"