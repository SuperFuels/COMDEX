from __future__ import annotations

from typing import Any, Dict, Optional


def _safe_get_number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_runtime_confidence_modifiers(
    *,
    pair_context: Optional[Dict[str, Any]] = None,
    credit_trajectory: Optional[Dict[str, Any]] = None,
    pre_earnings_estimate: Optional[Dict[str, Any]] = None,
    post_report_calibration: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    thesis_confidence_modifier = 0.0
    credit_drift_penalty = 0.0
    catalyst_conviction_modifier = 0.0
    calibration_modifier = 0.0
    active_flags: list[str] = []

    if pair_context:
        pair_conviction = _safe_get_number(
            pair_context.get("pair_score", {}).get("conviction"),
            0.0,
        )
        macro_score = _safe_get_number(
            pair_context.get("macro_coherence", {}).get("score"),
            0.0,
        )
        risk_state = pair_context.get("risk_appetite_signal", {}).get("state", "unknown")
        carry_state = pair_context.get("carry_signal", {}).get("state", "unknown")
        direction_bias = pair_context.get("pair_score", {}).get("direction_bias", "unknown")

        thesis_confidence_modifier += min(pair_conviction / 1000.0, 0.10)
        thesis_confidence_modifier += min(macro_score / 2000.0, 0.05)

        if risk_state == "risk_off":
            active_flags.append("pair_risk_off")
        elif risk_state == "risk_on":
            active_flags.append("pair_risk_on")

        if carry_state == "unwind_risk":
            thesis_confidence_modifier -= 0.05
            active_flags.append("carry_unwind_risk")
        elif carry_state in {"favour_base", "favour_quote"}:
            active_flags.append("carry_supportive")

        if direction_bias != "unknown":
            active_flags.append(f"pair_bias:{direction_bias}")

    if credit_trajectory:
        trajectory = credit_trajectory.get("trajectory", {})
        shadow_rating = credit_trajectory.get("shadow_rating", {})
        notes = str(trajectory.get("notes", "")).lower()

        direction = shadow_rating.get("direction", "unknown")
        confidence = _safe_get_number(shadow_rating.get("confidence"), 0.0)
        state = trajectory.get("state", "unknown")

        if direction == "deteriorating":
            credit_drift_penalty += min(confidence / 1000.0, 0.10)
            active_flags.append("credit_deteriorating")
        elif direction == "improving":
            thesis_confidence_modifier += min(confidence / 1500.0, 0.05)
            active_flags.append("credit_improving")

        if "momentum=accelerating" in notes:
            credit_drift_penalty += 0.03
            active_flags.append("credit_accelerating")
        elif "momentum=steady" in notes:
            active_flags.append("credit_steady")

        if state in {"downgrade_candidate", "fallen_angel_risk", "stressed"}:
            credit_drift_penalty += 0.05
            active_flags.append("downgrade_candidate")

        if state == "fallen_angel_risk":
            credit_drift_penalty += 0.04
            active_flags.append("fallen_angel_risk")

        if state in {"upgrade_candidate", "rising_star_candidate"}:
            thesis_confidence_modifier += 0.04
            active_flags.append("upgrade_candidate")

        if state == "rising_star_candidate":
            thesis_confidence_modifier += 0.03
            active_flags.append("rising_star_potential")

    if pre_earnings_estimate:
        divergence = pre_earnings_estimate.get("divergence", {})
        signal = pre_earnings_estimate.get("signal", {})

        div_score = _safe_get_number(divergence.get("divergence_score"), 0.0)
        div_conf = _safe_get_number(divergence.get("confidence"), 0.0)
        catalyst_strength = _safe_get_number(signal.get("catalyst_strength"), 0.0)

        catalyst_conviction_modifier += min(div_score / 1000.0, 0.10)
        catalyst_conviction_modifier += min(div_conf / 2000.0, 0.05)
        catalyst_conviction_modifier += min(catalyst_strength / 2000.0, 0.05)

        if signal.get("long_candidate"):
            active_flags.append("pre_earnings_long_candidate")
        if signal.get("short_candidate"):
            active_flags.append("pre_earnings_short_candidate")

    if post_report_calibration:
        prediction_comparison = post_report_calibration.get("prediction_comparison", {})
        confidence_drift = post_report_calibration.get("confidence_drift", {})

        prediction_quality = prediction_comparison.get("prediction_quality", "acceptable")
        previous_confidence = _safe_get_number(
            confidence_drift.get("previous_confidence"),
            0.0,
        )
        new_confidence = _safe_get_number(
            confidence_drift.get("new_confidence"),
            0.0,
        )

        drift_delta = new_confidence - previous_confidence
        calibration_modifier += drift_delta / 1000.0

        if prediction_quality == "strong":
            calibration_modifier += 0.01
            active_flags.append("well_calibrated_model")
        elif prediction_quality == "failed":
            calibration_modifier -= 0.02
            active_flags.append("poorly_calibrated_model")
        elif prediction_quality == "weak":
            calibration_modifier -= 0.01
            active_flags.append("weak_model_fit")
        elif prediction_quality == "acceptable":
            active_flags.append("acceptable_model_fit")

    combined = {
        "thesis_confidence_modifier": round(
            thesis_confidence_modifier + calibration_modifier,
            4,
        ),
        "credit_drift_penalty": round(credit_drift_penalty, 4),
        "catalyst_conviction_modifier": round(catalyst_conviction_modifier, 4),
        "calibration_modifier": round(calibration_modifier, 4),
        "active_flags": active_flags,
    }

    return {
        "pair_context": pair_context,
        "credit_trajectory": credit_trajectory,
        "pre_earnings_estimate": pre_earnings_estimate,
        "post_report_calibration": post_report_calibration,
        "combined": combined,
    }