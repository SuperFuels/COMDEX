# ──────────────────────────────────────────────────────────────
#  AION ↔ Field Control Bridge (v2.1)
#  Maps AION cognitive state → QQC / CFE control parameters
#  + Goal bias + adaptive shaping + decision-influence shaping
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Dict, Any, Optional


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


class AionFieldControlBridge:
    """
    Bridge between AION cognition and field control (QQC / CFE).

    DESIGN:
        - deterministic
        - bounded
        - fail-safe
        - no side effects
        - no persistence

    INPUT:
        AION cognitive + telemetry state

    OUTPUT:
        normalized control parameters for QQC / CFE
    """

    @staticmethod
    def map_to_field(aion_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert AION state → field control parameters

        Supported inputs (all optional):
            stability
            coherence
            drift
            focus
            depth
            awareness
            confidence
            tone
            reward
            global_coherence
            top_goal
            goal_count
            alignment_error
            reinforcement_learning_rate
            reinforcement_stability_factor
            decision_influence_bias
        """

        stability = _safe_float(aion_state.get("stability", aion_state.get("coherence", 0.5)))
        coherence = _safe_float(aion_state.get("coherence", stability))
        drift = abs(_safe_float(aion_state.get("drift", 0.0)))
        focus = _safe_float(aion_state.get("focus", 0.6))
        depth = _safe_float(aion_state.get("depth", 1.0))
        awareness = _safe_float(aion_state.get("awareness", 0.5))
        confidence = _safe_float(aion_state.get("confidence", 0.7))
        reward = _safe_float(aion_state.get("reward", 0.0))
        global_coherence = _safe_float(aion_state.get("global_coherence", coherence))
        alignment_error = abs(_safe_float(aion_state.get("alignment_error", 0.0)))

        reinforcement_learning_rate = _safe_float(
            aion_state.get("reinforcement_learning_rate", 0.1),
            0.1,
        )
        reinforcement_stability_factor = _safe_float(
            aion_state.get("reinforcement_stability_factor", 1.0),
            1.0,
        )

        tone = str(aion_state.get("tone", "neutral"))
        top_goal: Optional[str] = aion_state.get("top_goal")
        goal_count = int(aion_state.get("goal_count", 0) or 0)

        decision_influence_bias = aion_state.get("decision_influence_bias", {}) or {}
        if not isinstance(decision_influence_bias, dict):
            decision_influence_bias = {}

        field_stability_bias = _safe_float(decision_influence_bias.get("field_stability", 1.0), 1.0)
        field_drift_bias = _safe_float(decision_influence_bias.get("field_drift_response", 1.0), 1.0)
        field_instability_bias = _safe_float(decision_influence_bias.get("field_instability", 1.0), 1.0)
        field_reasoner_bias = _safe_float(decision_influence_bias.get("field_reasoner", 1.0), 1.0)

        stability = _clamp(stability, 0.0, 1.0)
        coherence = _clamp(coherence, 0.0, 1.0)
        drift = _clamp(drift, 0.0, 1.0)
        focus = _clamp(focus, 0.0, 1.0)
        awareness = _clamp(awareness, 0.0, 1.0)
        confidence = _clamp(confidence, 0.0, 1.0)
        global_coherence = _clamp(global_coherence, 0.0, 1.0)
        alignment_error = _clamp(alignment_error, 0.0, 1.0)
        reinforcement_learning_rate = _clamp(reinforcement_learning_rate, 0.0, 1.0)
        reinforcement_stability_factor = _clamp(reinforcement_stability_factor, 0.5, 2.0)
        field_stability_bias = _clamp(field_stability_bias, 0.0, 2.0)
        field_drift_bias = _clamp(field_drift_bias, 0.0, 2.0)
        field_instability_bias = _clamp(field_instability_bias, 0.5, 2.0)
        field_reasoner_bias = _clamp(field_reasoner_bias, 0.0, 2.0)

        # -------------------------------------------------
        # CORE CONTROL LAWS
        # -------------------------------------------------

        resonance_gain = _clamp(
            (stability * 0.45 * field_stability_bias)
            + (focus * 0.25)
            + (global_coherence * 0.15)
            + (min(1.0, reinforcement_stability_factor / 2.0) * 0.15),
            0.1,
            1.0,
        )

        symbolic_temperature = _clamp(
            (drift * 0.5 * field_drift_bias)
            + ((1.0 - confidence) * 0.2)
            + (alignment_error * 0.1)
            + ((field_instability_bias - 1.0) * 0.15)
            + (max(0.0, 0.15 - reward) * 0.2),
            0.0,
            1.0,
        )

        reasoning_depth = _clamp(
            depth * max(0.75, field_reasoner_bias),
            0.5,
            2.5,
        )

        stabilization_bias = _clamp(
            (1.0 - drift) * (1.0 / max(0.75, field_instability_bias)),
            0.0,
            1.0,
        )

        awareness_coupling = _clamp(
            awareness * (1.0 - alignment_error * 0.5),
            0.0,
            1.0,
        )

        # -------------------------------------------------
        # GOAL-DRIVEN MODULATION
        # -------------------------------------------------

        goal_bias = None
        control_priority = "maintain"

        if top_goal == "reduce_drift":
            stabilization_bias = _clamp(stabilization_bias + 0.2, 0.0, 1.0)
            symbolic_temperature = _clamp(symbolic_temperature * 0.8, 0.0, 1.0)
            control_priority = "stabilize"
            goal_bias = "drift_reduction"

        elif top_goal == "increase_coherence":
            resonance_gain = _clamp(resonance_gain + 0.15, 0.0, 1.0)
            awareness_coupling = _clamp(awareness_coupling + 0.1, 0.0, 1.0)
            control_priority = "amplify"
            goal_bias = "coherence_boost"

        elif top_goal == "stabilize_resonance":
            symbolic_temperature = _clamp(symbolic_temperature * 0.7, 0.0, 1.0)
            stabilization_bias = _clamp(stabilization_bias + 0.1, 0.0, 1.0)
            control_priority = "stabilize"
            goal_bias = "resonance_lock"

        if goal_count > 1:
            resonance_gain = _clamp(resonance_gain * 0.95, 0.0, 1.0)

        # -------------------------------------------------
        # REWARD / REINFORCEMENT MICRO-ADAPTATION
        # -------------------------------------------------

        if reward > 0:
            resonance_gain = _clamp(
                resonance_gain + min(0.05, reward * 0.05) + (reinforcement_learning_rate * 0.02),
                0.0,
                1.0,
            )
        elif reward < 0:
            symbolic_temperature = _clamp(
                symbolic_temperature + min(0.08, abs(reward) * 0.08),
                0.0,
                1.0,
            )

        if reinforcement_stability_factor > 1.0:
            stabilization_bias = _clamp(
                stabilization_bias + min(0.05, (reinforcement_stability_factor - 1.0) * 0.1),
                0.0,
                1.0,
            )

        return {
            "resonance_gain": resonance_gain,
            "symbolic_temperature": symbolic_temperature,
            "reasoning_depth": reasoning_depth,
            "stabilization_bias": stabilization_bias,
            "awareness_coupling": awareness_coupling,
            "mode": tone,
            "goal_bias": goal_bias,
            "control_priority": control_priority,
        }

    @staticmethod
    def telemetry_to_aion(telemetry: Dict[str, Any]) -> Dict[str, float]:
        coherence = _safe_float(telemetry.get("coherence", 0.5))
        drift = abs(_safe_float(telemetry.get("delta_phi", 0.0)))
        snr = _safe_float(telemetry.get("snr", 0.5))
        entropy = _safe_float(telemetry.get("entropy", 0.5))

        return {
            "stability": _clamp(coherence, 0.0, 1.0),
            "coherence": _clamp(coherence, 0.0, 1.0),
            "drift": _clamp(drift, 0.0, 1.0),
            "focus": _clamp(snr, 0.0, 1.0),
            "confidence": _clamp(coherence - entropy * 0.3, 0.0, 1.0),
        }

    @staticmethod
    def validate_control(control: Dict[str, Any]) -> Dict[str, Any]:
        safe = dict(control)

        safe["resonance_gain"] = _clamp(_safe_float(control.get("resonance_gain", 0.5)), 0.0, 1.0)
        safe["symbolic_temperature"] = _clamp(_safe_float(control.get("symbolic_temperature", 0.5)), 0.0, 1.0)
        safe["stabilization_bias"] = _clamp(_safe_float(control.get("stabilization_bias", 0.5)), 0.0, 1.0)
        safe["awareness_coupling"] = _clamp(_safe_float(control.get("awareness_coupling", 0.5)), 0.0, 1.0)
        safe["reasoning_depth"] = _clamp(_safe_float(control.get("reasoning_depth", 1.0)), 0.5, 2.5)
        safe["mode"] = str(control.get("mode", "neutral"))
        safe["goal_bias"] = control.get("goal_bias")
        safe["control_priority"] = str(control.get("control_priority", "maintain"))

        return safe