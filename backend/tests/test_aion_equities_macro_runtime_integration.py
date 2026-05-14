from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.intelligence_runtime import IntelligenceRuntime


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_bootstrap_company_intelligence_with_macro_context(tmp_path):
    rt = IntelligenceRuntime(tmp_path)

    macro = rt.macro_regime_store.save_macro_regime(
        as_of_date=_dt(2026, 2, 22, 8, 0, 0),
        regime_state="transition",
        summary="risk_off",
        generated_by="pytest",
        signals_patch={
            "usd_direction": "strengthening",
            "usd_jpy_signal": "risk_negative",
            "rates_direction": "rising",
            "real_yields_direction": "rising",
            "gold_direction": "rising",
            "credit_spread_regime": "widening",
        },
        risk_flags=[
            "yen_carry_unwind_risk",
            "credit_stress_rising",
        ],
        validate=True,
    )

    top_down = rt.top_down_levers_store.save_top_down_snapshot(
        snapshot_date="2026-02-22",
        generated_by="pytest",
        payload_patch={
            "fx": {
                "usd_broad": {"direction": "up"},
                "usd_jpy": {"direction": "down"},
            },
            "rates": {
                "real_yields": {"direction": "up"},
            },
            "credit": {
                "spreads": {"direction": "widening"},
            },
            "commodities": {
                "gold": {"direction": "up"},
                "oil": {"direction": "up"},
            },
            "sector_flows": {
                "defensives": {"direction": "into"},
                "energy": {"direction": "into"},
                "ai_infrastructure": {"direction": "out_of"},
            },
        },
        validate=True,
    )

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
        macro_regime_id=macro["macro_regime_id"],
        top_down_snapshot_id=top_down["snapshot_id"],
        validate=True,
    )

    assert result["helicopter_view"] is not None

    helicopter = result["helicopter_view"]

    assert helicopter["macro_regime"]["macro_regime_id"] == macro["macro_regime_id"]
    assert helicopter["macro_regime"]["summary"] == "risk_off"
    assert helicopter["top_down_snapshot"]["snapshot_id"] == top_down["snapshot_id"]
    assert helicopter["derived"]["sector_posture"]["defensives"] == "green"
    assert helicopter["derived"]["conviction_filter"]["contradiction_count"] >= 1
    assert len(result["edges"]) == 5