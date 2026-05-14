from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.intelligence_runtime import IntelligenceRuntime


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_bootstrap_company_intelligence_with_pair_context(tmp_path):
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
            "active_levers": [
                {"lever": "dollar", "direction": "up", "materiality": 80.0},
                {"lever": "yen", "direction": "risk_off", "materiality": 78.0},
                {"lever": "real_yields", "direction": "up", "materiality": 74.0},
                {"lever": "credit_spreads", "direction": "up", "materiality": 84.0},
                {"lever": "gold", "direction": "up", "materiality": 62.0},
            ],
            "cascade_implications": [
                {
                    "rule_id": "credit_spreads_widening",
                    "summary": "Pressure on high debt and cyclical names",
                    "affected_scope": "sector",
                    "effect_direction": "headwind",
                    "confidence": 88.0,
                    "target_refs": ["sector/cyclicals"],
                }
            ],
            "sector_posture": [
                {
                    "sector_ref": "sector/defensives",
                    "posture": "green",
                    "tailwind_score": 78.0,
                    "headwind_score": 20.0,
                },
                {
                    "sector_ref": "sector/cyclicals",
                    "posture": "red",
                    "tailwind_score": 18.0,
                    "headwind_score": 81.0,
                },
            ],
            "conviction_state": {
                "signal_coherence": 58.0,
                "uncertainty_score": 44.0,
                "summary": "Mixed but risk-off leaning",
            },
        },
        validate=True,
    )

    pair_ctx = rt.pair_context_store.save_pair_context(
        pair="GBPUSD",
        base_country_ref="country/GB",
        quote_country_ref="country/US",
        as_of_date=_dt(2026, 2, 22, 9, 0, 0),
        generated_by="pytest",
        macro_coherence_patch={
            "score": 82.0,
            "regime_alignment": "supportive",
            "notes": "USD strength remains dominant",
        },
        carry_signal_patch={
            "state": "favour_quote",
            "strength": 79.0,
            "notes": "Yield differential remains USD-supportive",
        },
        risk_appetite_signal_patch={
            "state": "risk_off",
            "confidence": 76.0,
            "notes": "Carry unwind risk still elevated",
        },
        pair_score_patch={
            "direction_bias": "quote_outperform",
            "conviction": 79.0,
            "summary": "USD likely to outperform GBP in current regime",
        },
        linked_refs_patch={
            "country_ambassador_refs": ["country/GB", "country/US"],
            "country_relationship_refs": ["relationship/GB_US"],
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
        pair_context_id=pair_ctx["pair_context_id"],
        validate=True,
    )

    helicopter = result["helicopter_view"]

    assert helicopter is not None
    assert helicopter["pair_context"]["pair_context_id"] == pair_ctx["pair_context_id"]
    assert helicopter["pair_context"]["macro_coherence"]["score"] == 82.0
    assert helicopter["pair_context"]["pair_score"]["direction_bias"] == "quote_outperform"
    assert helicopter["derived"]["conviction_filter"]["contradiction_count"] >= 1
    assert len(result["edges"]) == 6

    assert any(
        e["src"] == pair_ctx["pair_context_id"] and e["dst"] == result["thesis"]["thesis_id"]
        for e in result["edges"]
    )