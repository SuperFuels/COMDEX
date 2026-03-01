from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.intelligence_runtime import IntelligenceRuntime


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_build_runtime_confidence_modifiers_combines_all_layers(tmp_path):
    rt = IntelligenceRuntime(tmp_path)

    pair_ctx = rt.pair_context_store.save_pair_context(
        pair="GBPUSD",
        base_country_ref="country/GB",
        quote_country_ref="country/US",
        as_of_date="2026-02-22",
        generated_by="pytest",
        macro_coherence_patch={
            "score": 82.0,
            "regime_alignment": "supportive",
            "notes": "USD strength coherent with macro backdrop",
        },
        carry_signal_patch={
            "state": "favour_quote",
            "strength": 74.0,
            "notes": "USD carry remains supportive",
        },
        risk_appetite_signal_patch={
            "state": "risk_off",
            "confidence": 79.0,
            "notes": "Risk-off regime supports USD",
        },
        pair_score_patch={
            "direction_bias": "quote_outperform",
            "conviction": 81.0,
            "summary": "USD bias remains dominant",
        },
        validate=True,
    )

    credit = rt.credit_trajectory_store.save_credit_trajectory(
        entity_ref="company/AHT.L",
        entity_type="company",
        as_of_date="2026-02-22",
        generated_by="pytest",
        rating_state_patch={
            "current_rating": "BBB-",
            "rating_agency_mix": ["sp", "fitch"],
            "outlook": "negative",
        },
        trajectory_patch={
            "direction": "deteriorating",
            "momentum": "accelerating",
            "confidence": 77.0,
        },
        catalyst_flags_patch={
            "downgrade_candidate": True,
            "upgrade_candidate": False,
            "fallen_angel_risk": True,
            "rising_star_potential": False,
        },
        validate=True,
    )

    pre = rt.pre_earnings_estimate_store.save_pre_earnings_estimate(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026Q2_pre_earnings",
        as_of_date="2026-02-22",
        generated_by="pytest",
        estimate_patch={
            "revenue_impact_pct": 2.8,
            "margin_impact_bps": 65.0,
            "eps_impact_pct": 4.2,
        },
        consensus_patch={
            "street_revenue_impact_pct": 0.8,
            "street_margin_impact_bps": 15.0,
            "street_eps_impact_pct": 1.0,
        },
        divergence_patch={
            "divergence_score": 72.0,
            "direction": "above_consensus",
            "confidence": 75.0,
        },
        signal_patch={
            "long_candidate": True,
            "short_candidate": False,
            "catalyst_strength": 71.0,
        },
        validate=True,
    )

    calibration = rt.post_report_calibration_store.save_post_report_calibration(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026Q1",
        as_of_date="2026-02-22",
        generated_by="pytest",
        prediction_quality_patch={
            "direction_correct": True,
            "magnitude_error_pct": 8.0,
            "confidence_calibration_score": 83.0,
        },
        adjustment_patch={
            "sensitivity_update_strength": 22.0,
            "lag_update_days": -3,
            "guidance_bias_shift": "stable",
        },
        learning_patch={
            "confidence_penalty_bps": 0.0,
            "confidence_boost_bps": 18.0,
            "notes": "Recent calibration improved trust in model outputs",
        },
        validate=True,
    )

    out = rt.build_runtime_confidence_modifiers(
        ticker="AHT.L",
        thesis_window="2026Q2_pre_earnings",
        pair_context_id=pair_ctx["pair_context_id"],
        credit_trajectory_id=credit["credit_trajectory_id"],
        pre_earnings_estimate_id=pre["pre_earnings_estimate_id"],
        post_report_calibration_id=calibration["post_report_calibration_id"],
    )

    assert out["pair_context"]["pair_context_id"] == pair_ctx["pair_context_id"]
    assert out["credit_trajectory"]["credit_trajectory_id"] == credit["credit_trajectory_id"]
    assert out["pre_earnings_estimate"]["pre_earnings_estimate_id"] == pre["pre_earnings_estimate_id"]
    assert out["post_report_calibration"]["post_report_calibration_id"] == calibration["post_report_calibration_id"]

    combined = out["combined"]
    assert combined["thesis_confidence_modifier"] != 0.0
    assert combined["credit_drift_penalty"] > 0.0
    assert combined["catalyst_conviction_modifier"] > 0.0
    assert combined["calibration_modifier"] >= 0.0
    assert len(combined["active_flags"]) >= 3


def test_bootstrap_company_intelligence_applies_runtime_confidence_modifiers(tmp_path):
    rt = IntelligenceRuntime(tmp_path)

    pair_ctx = rt.pair_context_store.save_pair_context(
        pair="GBPUSD",
        base_country_ref="country/GB",
        quote_country_ref="country/US",
        as_of_date="2026-02-22",
        generated_by="pytest",
        macro_coherence_patch={
            "score": 78.0,
            "regime_alignment": "supportive",
        },
        carry_signal_patch={
            "state": "favour_quote",
            "strength": 68.0,
        },
        risk_appetite_signal_patch={
            "state": "risk_off",
            "confidence": 74.0,
        },
        pair_score_patch={
            "direction_bias": "quote_outperform",
            "conviction": 76.0,
            "summary": "USD supportive vs GBP",
        },
        validate=True,
    )

    credit = rt.credit_trajectory_store.save_credit_trajectory(
        entity_ref="company/AHT.L",
        entity_type="company",
        as_of_date="2026-02-22",
        generated_by="pytest",
        trajectory_patch={
            "direction": "deteriorating",
            "momentum": "steady",
            "confidence": 66.0,
        },
        catalyst_flags_patch={
            "downgrade_candidate": True,
            "fallen_angel_risk": False,
            "upgrade_candidate": False,
            "rising_star_potential": False,
        },
        validate=True,
    )

    pre = rt.pre_earnings_estimate_store.save_pre_earnings_estimate(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026Q2_pre_earnings",
        as_of_date="2026-02-22",
        generated_by="pytest",
        divergence_patch={
            "divergence_score": 64.0,
            "direction": "above_consensus",
            "confidence": 70.0,
        },
        signal_patch={
            "long_candidate": True,
            "short_candidate": False,
            "catalyst_strength": 67.0,
        },
        validate=True,
    )

    calibration = rt.post_report_calibration_store.save_post_report_calibration(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026Q1",
        as_of_date="2026-02-22",
        generated_by="pytest",
        learning_patch={
            "confidence_penalty_bps": 0.0,
            "confidence_boost_bps": 12.0,
            "notes": "Recent prediction quality strong",
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
            "risk": {"notes": "bootstrap"},
            "catalyst": {
                "has_active_catalyst": True,
                "catalyst_count": 1,
            },
        },
        pair_context_id=pair_ctx["pair_context_id"],
        credit_trajectory_id=credit["credit_trajectory_id"],
        pre_earnings_estimate_id=pre["pre_earnings_estimate_id"],
        post_report_calibration_id=calibration["post_report_calibration_id"],
        validate=True,
    )

    modifiers = result["runtime_confidence_modifiers"]
    assert modifiers is not None
    assert modifiers["combined"]["thesis_confidence_modifier"] != 0.0
    assert modifiers["combined"]["credit_drift_penalty"] > 0.0
    assert modifiers["combined"]["catalyst_conviction_modifier"] > 0.0

    assert len(result["edges"]) >= 5
    assert any(
        e["link_type"] == "confidence_modifier"
        and e["src"] == pair_ctx["pair_context_id"]
        for e in result["edges"]
    )


def test_runtime_confidence_modifiers_handles_missing_optional_layers(tmp_path):
    rt = IntelligenceRuntime(tmp_path)

    out = rt.build_runtime_confidence_modifiers(
        ticker="AHT.L",
        thesis_window="2026Q2_pre_earnings",
        pair_context_id=None,
        credit_trajectory_id=None,
        pre_earnings_estimate_id=None,
        post_report_calibration_id=None,
    )

    assert out["pair_context"] is None
    assert out["credit_trajectory"] is None
    assert out["pre_earnings_estimate"] is None
    assert out["post_report_calibration"] is None
    assert out["combined"]["thesis_confidence_modifier"] == 0.0
    assert out["combined"]["credit_drift_penalty"] == 0.0
    assert out["combined"]["catalyst_conviction_modifier"] == 0.0
    assert out["combined"]["calibration_modifier"] == 0.0
    assert out["combined"]["active_flags"] == []