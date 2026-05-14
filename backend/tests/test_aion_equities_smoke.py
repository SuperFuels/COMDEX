from backend.modules.aion_equities import get_schema_path, build_sqi_signal_inputs


def test_aion_equities_schema_registry_and_sqi_mapping_smoke():
    path = get_schema_path("assessment")
    assert path.exists()

    assessment = {
        "schema_version": "v0.1.0",
        "assessment_id": "assessment/AHT.L/2026Q1",
        "entity_id": "company/AHT.L",
        "as_of": "2026-02-22T22:00:00Z",
        "bqs": {
            "score": 0.78,
            "components": {
                "revenue_trajectory_quality": {"value": 0.75, "confidence": 0.8},
                "margin_direction_resilience": {"value": 0.72, "confidence": 0.7}
            }
        },
        "acs": {
            "score": 0.83,
            "components": {
                "narrative_coherence": {"value": 0.81, "confidence": 0.76},
                "historical_model_error_stability": {"value": 0.79, "confidence": 0.74},
                "regulatory_complexity": {"value": 0.20, "confidence": 0.6}
            }
        },
        "aot": {
            "automation_beneficiary_score": 0.66,
            "automation_threat_score": 0.28,
            "signals": {
                "management_execution_credibility": {"value": 0.77, "confidence": 0.7},
                "debt_blocks_transition": {"value": 0.15, "confidence": 0.8}
            }
        },
        "risk": {
            "analytical_confidence_gate_pass": True,
            "borrow_cost_estimate_annualized_pct": 1.25,
            "position_risk_flags": []
        },
        "catalyst": {
            "has_active_catalyst": True,
            "next_catalyst_date": "2026-06-18",
            "timing_confidence": 0.71,
            "catalyst_types": ["earnings"]
        }
    }

    signals = build_sqi_signal_inputs(
        assessment=assessment,
        context={
            "kg": {
                "supports_count": 4,
                "contradicts_count": 1,
                "drift_score": 0.12,
                "confidence_modifier": 0.05,
                "pattern_match_score": 0.62,
            },
            "pattern": {
                "aggregate_score": 0.58,
                "stability_modifier": 0.04
            },
            "observer": {
                "bias_penalty": 0.0
            }
        }
    )

    assert signals["sqi.business_strength_signal"] == 0.78
    assert signals["sqi.predictability_signal"] == 0.83
    assert signals["policy_gate.acs_pass"] is True
    assert signals["sqi.kg_net_support_signal"] == 3