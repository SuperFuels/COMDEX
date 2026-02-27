from __future__ import annotations

from typing import Any, Dict, Optional


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y"}:
            return True
        if v in {"false", "0", "no", "n"}:
            return False
    return bool(value)


def _clamp_0_100(value: Any) -> float:
    v = _num(value, 0.0)
    if v < 0.0:
        return 0.0
    if v > 100.0:
        return 100.0
    return v


def _component_value(obj: Dict[str, Any], key: str, field: str = "value", default: float = 0.0) -> float:
    comp = (obj or {}).get(key, {})
    if isinstance(comp, dict):
        return _clamp_0_100(comp.get(field, default))
    return _clamp_0_100(default)


def _safe_len(value: Any) -> int:
    if isinstance(value, (list, tuple, set)):
        return len(value)
    return 0


def _normalize_pattern_score(value: Any) -> float:
    """
    Accepts either 0..1 or 0..100.
    """
    v = _num(value, 0.0)
    if v <= 1.0:
        v *= 100.0
    return _clamp_0_100(v)


def _normalize_bias_penalty(value: Any) -> float:
    """
    Accepts either 0..1 or 0..100.
    """
    v = _num(value, 0.0)
    if v <= 1.0:
        v *= 100.0
    return _clamp_0_100(v)


def build_sqi_signal_inputs(
    *,
    assessment: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Bridge contract:
      assessment -> SQI-ready signal inputs

    Returns a normalized dict of 0..100 signals plus hard policy flags.

    context shape (optional):
    {
      "kg": {
        "supports_count": 4,
        "contradicts_count": 1,
        "drift_score": 12.0,              # 0..100 preferred, 0..1 tolerated
        "confidence_modifier": 5.0,       # 0..100 preferred, 0..1 tolerated
        "pattern_match_score": 62.0       # 0..100 preferred, 0..1 tolerated
      },
      "pattern": {
        "aggregate_score": 58.0,          # 0..100 preferred, 0..1 tolerated
        "stability_modifier": 4.0         # 0..100 preferred, 0..1 tolerated
      },
      "observer": {
        "bias_penalty": 0.0               # 0..100 preferred, 0..1 tolerated
      }
    }
    """
    context = context or {}
    kg = context.get("kg", {}) if isinstance(context.get("kg"), dict) else {}
    pattern = context.get("pattern", {}) if isinstance(context.get("pattern"), dict) else {}
    observer = context.get("observer", {}) if isinstance(context.get("observer"), dict) else {}

    bqs = assessment.get("bqs", {}) if isinstance(assessment.get("bqs"), dict) else {}
    acs = assessment.get("acs", {}) if isinstance(assessment.get("acs"), dict) else {}
    aot = assessment.get("aot", {}) if isinstance(assessment.get("aot"), dict) else {}
    risk = assessment.get("risk", {}) if isinstance(assessment.get("risk"), dict) else {}
    catalyst = assessment.get("catalyst", {}) if isinstance(assessment.get("catalyst"), dict) else {}

    bqs_components = bqs.get("components", {}) if isinstance(bqs.get("components"), dict) else {}
    acs_components = acs.get("components", {}) if isinstance(acs.get("components"), dict) else {}
    aot_signals = aot.get("signals", {}) if isinstance(aot.get("signals"), dict) else {}

    supports_count = _safe_len(kg.get("supports", [])) or int(_num(kg.get("supports_count", 0), 0))
    contradicts_count = _safe_len(kg.get("contradictions", [])) or int(_num(kg.get("contradicts_count", 0), 0))

    contradiction_pressure = 0.0
    total_links = supports_count + contradicts_count
    if total_links > 0:
        contradiction_pressure = (contradicts_count / total_links) * 100.0

    # explicit risk flags also add contradiction pressure
    contradiction_pressure += min(25.0, 5.0 * _safe_len(risk.get("position_risk_flags", [])))
    contradiction_pressure = _clamp_0_100(contradiction_pressure)

    drift_score = _normalize_pattern_score(kg.get("drift_score", 0.0))
    confidence_modifier = _normalize_pattern_score(kg.get("confidence_modifier", 0.0))
    kg_pattern_support = _normalize_pattern_score(kg.get("pattern_match_score", 0.0))
    pattern_support = _normalize_pattern_score(pattern.get("aggregate_score", 0.0))
    stability_modifier = _normalize_pattern_score(pattern.get("stability_modifier", 0.0))
    bias_penalty = _normalize_bias_penalty(observer.get("bias_penalty", 0.0))

    catalyst_alignment_signal = 100.0 if _bool(catalyst.get("has_active_catalyst", False)) else 0.0
    catalyst_timing_confidence = _clamp_0_100(catalyst.get("timing_confidence", 0.0))

    short_borrow_penalty = min(
        100.0,
        _clamp_0_100(risk.get("borrow_cost_estimate_annualized_pct", 0.0)) * 5.0,
    )

    evidence_component_signals = {
        "revenue_trajectory_quality": _component_value(bqs_components, "revenue_trajectory_quality"),
        "margin_direction_resilience": _component_value(bqs_components, "margin_direction_resilience"),
        "fcf_generation_quality": _component_value(bqs_components, "fcf_generation_quality"),
        "balance_sheet_strength": _component_value(bqs_components, "balance_sheet_strength"),
        "debt_maturity_refinancing_risk": _component_value(bqs_components, "debt_maturity_refinancing_risk"),
        "interest_coverage_quality": _component_value(bqs_components, "interest_coverage_quality"),
        "moat_durability": _component_value(bqs_components, "moat_durability"),
        "management_credibility_guidance_accuracy": _component_value(
            bqs_components, "management_credibility_guidance_accuracy"
        ),
        "capital_allocation_discipline": _component_value(bqs_components, "capital_allocation_discipline"),
    }

    evidence_confidence_weights = {
        "revenue_trajectory_quality": _component_value(bqs_components, "revenue_trajectory_quality", "confidence"),
        "margin_direction_resilience": _component_value(bqs_components, "margin_direction_resilience", "confidence"),
        "fcf_generation_quality": _component_value(bqs_components, "fcf_generation_quality", "confidence"),
        "balance_sheet_strength": _component_value(bqs_components, "balance_sheet_strength", "confidence"),
        "debt_maturity_refinancing_risk": _component_value(
            bqs_components, "debt_maturity_refinancing_risk", "confidence"
        ),
        "interest_coverage_quality": _component_value(bqs_components, "interest_coverage_quality", "confidence"),
        "moat_durability": _component_value(bqs_components, "moat_durability", "confidence"),
        "management_credibility_guidance_accuracy": _component_value(
            bqs_components, "management_credibility_guidance_accuracy", "confidence"
        ),
        "capital_allocation_discipline": _component_value(
            bqs_components, "capital_allocation_discipline", "confidence"
        ),
    }

    uncertainty_penalty_signals = {
        "commodity_input_opacity": _component_value(acs_components, "commodity_input_opacity"),
        "hedging_book_opacity": _component_value(acs_components, "hedging_book_opacity"),
        "regulatory_complexity": _component_value(acs_components, "regulatory_complexity"),
        "segment_complexity": _component_value(acs_components, "segment_complexity"),
    }

    avg_uncertainty_penalty = (
        sum(uncertainty_penalty_signals.values()) / len(uncertainty_penalty_signals)
        if uncertainty_penalty_signals
        else 0.0
    )

    coherence_score = (
        0.30 * _clamp_0_100(bqs.get("score", 0.0))
        + 0.25 * _clamp_0_100(acs.get("score", 0.0))
        + 0.10 * _clamp_0_100(aot.get("automation_beneficiary_score", 0.0))
        + 0.10 * catalyst_alignment_signal
        + 0.10 * catalyst_timing_confidence
        + 0.05 * kg_pattern_support
        + 0.05 * pattern_support
        + 0.05 * confidence_modifier
        - 0.15 * (contradiction_pressure / 100.0) * 100.0
        - 0.10 * (drift_score / 100.0) * 100.0
        - 0.10 * (avg_uncertainty_penalty / 100.0) * 100.0
        - 0.05 * (bias_penalty / 100.0) * 100.0
    )
    coherence_score = _clamp_0_100(coherence_score)

    stability_score = _clamp_0_100(
        0.45 * _component_value(acs_components, "historical_model_error_stability")
        + 0.25 * _component_value(acs_components, "narrative_coherence")
        + 0.15 * (100.0 - drift_score)
        + 0.15 * stability_modifier
    )

    collapse_readiness_score = _clamp_0_100(
        0.50 * coherence_score
        + 0.20 * stability_score
        + 0.15 * catalyst_alignment_signal
        + 0.15 * catalyst_timing_confidence
        - 0.10 * contradiction_pressure
        - 0.10 * short_borrow_penalty
    )

    signals = {
        # direct bridge contract
        "business_strength_signal": _clamp_0_100(bqs.get("score", 0.0)),
        "evidence_component_signals": evidence_component_signals,
        "evidence_confidence_weights": evidence_confidence_weights,

        "predictability_signal": _clamp_0_100(acs.get("score", 0.0)),
        "narrative_coherence_signal": _component_value(acs_components, "narrative_coherence"),
        "model_stability_signal": _component_value(acs_components, "historical_model_error_stability"),
        "uncertainty_penalty_signals": uncertainty_penalty_signals,

        "forward_margin_expansion_signal": _clamp_0_100(aot.get("automation_beneficiary_score", 0.0)),
        "disruption_threat_signal": _clamp_0_100(aot.get("automation_threat_score", 0.0)),
        "execution_credibility_signal": _component_value(aot_signals, "management_execution_credibility"),
        "transition_blocker_penalty": _component_value(aot_signals, "debt_blocks_transition"),

        "catalyst_alignment_signal": catalyst_alignment_signal,
        "timing_alignment_input": 100.0 if catalyst.get("next_catalyst_date") else 0.0,
        "catalyst_timing_confidence": catalyst_timing_confidence,

        "coherence_signal": coherence_score,
        "drift_score": drift_score,
        "contradiction_pressure": contradiction_pressure,
        "pattern_support_signal": max(kg_pattern_support, pattern_support),
        "stability_score": stability_score,
        "collapse_readiness_score": collapse_readiness_score,

        "short_net_return_penalty": short_borrow_penalty,
        "bias_penalty": bias_penalty,

        # hard/policy gates
        "policy_gate": {
            "acs_pass": _bool(risk.get("analytical_confidence_gate_pass", False)),
            "short_requires_catalyst": _bool(risk.get("short_requires_catalyst", True), True),
            "has_active_catalyst": _bool(catalyst.get("has_active_catalyst", False)),
        },

        # raw counts/context
        "kg_supports_count": supports_count,
        "kg_contradicts_count": contradicts_count,
    }

    return signals