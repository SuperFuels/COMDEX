from __future__ import annotations

from backend.modules.aion_equities import build_sqi_signal_inputs


def _sample_assessment():
    return {
        "version": "v0.1.0",
        "assessment_id": "assessment/company_AHT.L/2026-02-22T22:00:00Z",
        "entity_id": "company/AHT.L",
        "entity_type": "company",
        "as_of": "2026-02-22T22:00:00Z",
        "bqs": {
            "score": 78.0,
            "scale": "0-100",
            "components": {
                "revenue_trajectory_quality": {"value": 75.0, "confidence": 80.0},
                "margin_direction_resilience": {"value": 72.0, "confidence": 70.0},
                "fcf_generation_quality": {"value": 77.0, "confidence": 70.0},
                "balance_sheet_strength": {"value": 74.0, "confidence": 72.0},
                "debt_maturity_refinancing_risk": {"value": 32.0, "confidence": 66.0},
                "interest_coverage_quality": {"value": 81.0, "confidence": 74.0},
                "moat_durability": {"value": 76.0, "confidence": 65.0},
                "management_credibility_guidance_accuracy": {"value": 73.0, "confidence": 67.0},
                "capital_allocation_discipline": {"value": 71.0, "confidence": 64.0},
            },
        },
        "acs": {
            "score": 83.0,
            "scale": "0-100",
            "components": {
                "public_data_clarity": {"value": 86.0, "confidence": 80.0},
                "reporting_consistency": {"value": 84.0, "confidence": 78.0},
                "earnings_predictability": {"value": 79.0, "confidence": 75.0},
                "commodity_input_opacity": {"value": 22.0, "confidence": 65.0},
                "hedging_book_opacity": {"value": 18.0, "confidence": 60.0},
                "regulatory_complexity": {"value": 20.0, "confidence": 60.0},
                "segment_complexity": {"value": 32.0, "confidence": 61.0},
                "narrative_coherence": {"value": 81.0, "confidence": 76.0},
                "historical_model_error_stability": {"value": 79.0, "confidence": 74.0},
            },
        },
        "aot": {
            "automation_beneficiary_score": 66.0,
            "automation_threat_score": 28.0,
            "signals": {
                "estimated_automatable_cost_base_pct": 41.0,
                "capex_ability_to_automate": {"value": 69.0, "confidence": 70.0},
                "management_execution_credibility": {"value": 77.0, "confidence": 70.0},
                "debt_blocks_transition": {"value": 15.0, "confidence": 80.0},
                "customer_substitution_risk": {"value": 21.0, "confidence": 66.0},
                "sector_ai_adoption_pace": {"value": 58.0, "confidence": 63.0},
            },
        },
        "risk": {
            "analytical_confidence_gate_pass": True,
            "short_requires_catalyst": True,
            "borrow_cost_estimate_annualized_pct": 1.25,
            "position_risk_flags": [],
            "notes": "bootstrap",
        },
        "catalyst": {
            "has_active_catalyst": True,
            "catalyst_count": 1,
            "next_catalyst_date": "2026-06-18",
            "catalyst_types": ["earnings"],
            "timing_confidence": 71.0,
        },
        "provenance": {
            "source_event_ids": ["company/AHT.L/quarter/2026-Q1"],
            "source_hashes": [],
            "generated_by": "pytest",
            "generated_at": "2026-02-22T22:00:00Z",
        },
    }


def test_build_sqi_signal_inputs_maps_core_fields():
    assessment = _sample_assessment()

    signals = build_sqi_signal_inputs(
        assessment=assessment,
        context={
            "kg": {
                "supports_count": 4,
                "contradicts_count": 1,
                "drift_score": 12.0,
                "confidence_modifier": 5.0,
                "pattern_match_score": 62.0,
            },
            "pattern": {
                "aggregate_score": 58.0,
                "stability_modifier": 4.0,
            },
            "observer": {
                "bias_penalty": 0.0,
            },
        },
    )

    assert signals["business_strength_signal"] == 78.0
    assert signals["predictability_signal"] == 83.0
    assert signals["forward_margin_expansion_signal"] == 66.0
    assert signals["disruption_threat_signal"] == 28.0
    assert signals["execution_credibility_signal"] == 77.0
    assert signals["transition_blocker_penalty"] == 15.0
    assert signals["catalyst_alignment_signal"] == 100.0
    assert signals["catalyst_timing_confidence"] == 71.0
    assert signals["kg_supports_count"] == 4
    assert signals["kg_contradicts_count"] == 1
    assert 0.0 <= signals["coherence_signal"] <= 100.0
    assert 0.0 <= signals["stability_score"] <= 100.0
    assert 0.0 <= signals["collapse_readiness_score"] <= 100.0


def test_build_sqi_signal_inputs_sets_policy_flags():
    assessment = _sample_assessment()
    assessment["risk"]["analytical_confidence_gate_pass"] = False
    assessment["catalyst"]["has_active_catalyst"] = False

    signals = build_sqi_signal_inputs(assessment=assessment, context={})

    assert signals["policy_gate"]["acs_pass"] is False
    assert signals["policy_gate"]["short_requires_catalyst"] is True
    assert signals["policy_gate"]["has_active_catalyst"] is False
    assert signals["catalyst_alignment_signal"] == 0.0


def test_build_sqi_signal_inputs_handles_ratio_style_context_values():
    assessment = _sample_assessment()

    signals = build_sqi_signal_inputs(
        assessment=assessment,
        context={
            "kg": {
                "supports_count": 3,
                "contradicts_count": 1,
                "drift_score": 0.12,
                "confidence_modifier": 0.05,
                "pattern_match_score": 0.62,
            },
            "pattern": {
                "aggregate_score": 0.58,
                "stability_modifier": 0.04,
            },
            "observer": {
                "bias_penalty": 0.01,
            },
        },
    )

    assert signals["drift_score"] == 12.0
    assert signals["pattern_support_signal"] == 62.0
    assert signals["bias_penalty"] == 1.0