from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.intelligence_runtime import IntelligenceRuntime


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_bootstrap_company_intelligence_end_to_end(tmp_path):
    rt = IntelligenceRuntime(tmp_path)

    result = rt.bootstrap_company_intelligence(
        ticker="AHT.L",
        name="Ashtead Group plc",
        exchange="LSE",
        currency="GBP",
        sector_name="industrial_equipment_rental",
        industry="Equipment Rental",
        country="GB",
        company_status="active",
        acs_band="high",
        sector_confidence_tier="tier_1",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        thesis_mode="long",
        thesis_window="2026Q2_pre_earnings",
        thesis_status="candidate",
        assessment_payload_patch={
            "provenance": {
                "source_event_ids": ["company/AHT.L/quarter/2026-Q1"],
                "source_hashes": ["sha256:test"],
            },
            "risk": {
                "notes": "bootstrap",
            },
            "catalyst": {
                "has_active_catalyst": False,
                "catalyst_count": 0,
            },
        },
        validate=True,
    )

    assert result["company"]["company_id"] == "company/AHT.L"
    assert result["assessment"]["entity_id"] == "company/AHT.L"
    assert result["thesis"]["ticker"] == "AHT.L"
    assert len(result["edges"]) == 3

    sqi = result["sqi_signals"]
    assert "sqi.business_strength_signal" in sqi
    assert "sqi.predictability_signal" in sqi


def test_load_company_intelligence_snapshot(tmp_path):
    rt = IntelligenceRuntime(tmp_path)

    rt.bootstrap_company_intelligence(
        ticker="AHT.L",
        name="Ashtead Group plc",
        exchange="LSE",
        currency="GBP",
        sector_name="industrial_equipment_rental",
        industry="Equipment Rental",
        country="GB",
        company_status="active",
        acs_band="high",
        sector_confidence_tier="tier_1",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        thesis_mode="long",
        thesis_window="2026Q2_pre_earnings",
        thesis_status="candidate",
        assessment_payload_patch={
            "provenance": {
                "source_event_ids": ["company/AHT.L/quarter/2026-Q1"],
                "source_hashes": ["sha256:test"],
            },
            "risk": {
                "notes": "bootstrap",
            },
            "catalyst": {
                "has_active_catalyst": False,
                "catalyst_count": 0,
            },
        },
        validate=True,
    )

    snap = rt.load_company_intelligence_snapshot(
        ticker="AHT.L",
        mode="long",
        window="2026Q2_pre_earnings",
    )

    assert snap["company"]["ticker"] == "AHT.L"
    assert snap["assessment"]["entity_id"] == "company/AHT.L"
    assert snap["thesis"]["mode"] == "long"


def test_bootstrap_updates_company_intelligence_state_refs(tmp_path):
    rt = IntelligenceRuntime(tmp_path)

    result = rt.bootstrap_company_intelligence(
        ticker="AHT.L",
        name="Ashtead Group plc",
        exchange="LSE",
        currency="GBP",
        sector_name="industrial_equipment_rental",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        thesis_mode="long",
        thesis_window="bootstrap",
        assessment_payload_patch={
            "provenance": {
                "source_event_ids": ["company/AHT.L/quarter/2026-Q1"],
                "source_hashes": [],
            },
            "risk": {
                "notes": "bootstrap",
            },
            "catalyst": {
                "has_active_catalyst": False,
                "catalyst_count": 0,
            },
        },
        validate=True,
    )

    company = result["company"]
    assessment = result["assessment"]
    thesis = result["thesis"]

    assert company["intelligence_state"]["latest_assessment_ref"] == assessment["assessment_id"]
    assert thesis["thesis_id"] in company["intelligence_state"]["active_thesis_refs"]