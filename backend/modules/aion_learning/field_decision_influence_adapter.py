from __future__ import annotations

from typing import Any, Dict, List, Optional
import time
import uuid

from backend.modules.aion_learning.contracts_decision_influence import (
    DecisionInfluenceUpdate,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


class FieldDecisionInfluenceAdapter:
    """
    Adapter for converting field/cognitive feedback into a governed
    DecisionInfluenceUpdate payload.

    PURPOSE
    -------
    Owns:
      - reward/coherence/drift -> DecisionInfluenceUpdate
      - bounded mappings
      - metadata packing
      - future tuning rules

    DESIGN
    ------
      - deterministic
      - bounded
      - additive
      - no persistence
      - no side effects
      - contract-safe output only
    """

    DEFAULT_SOURCE = "hexcore_field_feedback"
    DEFAULT_REASON = "reward_to_decision_influence"

    @staticmethod
    def build_update(
        *,
        session_id: str,
        reward: float,
        coherence: float,
        dphi: float,
        self_awareness: float = 0.5,
        phi: float = 0.0,
        goal_suggestions: Optional[List[str]] = None,
        reinforcement: Optional[Dict[str, Any]] = None,
        emotion: str = "neutral",
        turn_id: Optional[str] = None,
        source: str = DEFAULT_SOURCE,
        reason: str = DEFAULT_REASON,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionInfluenceUpdate:
        """
        Build a typed, validated DecisionInfluenceUpdate from field signals.

        Allowed runtime sections:
          - setup_confidence_weights
          - pair_session_preferences
          - stand_down_sensitivity
          - llm_trust_weights
          - event_caution_multipliers
        """
        reward = _clamp(_safe_float(reward, 0.0), -1.0, 1.0)
        coherence = _clamp(_safe_float(coherence, 0.5), 0.0, 1.0)
        drift = _clamp(abs(_safe_float(dphi, 0.0)), 0.0, 1.0)
        self_awareness = _clamp(_safe_float(self_awareness, 0.5), 0.0, 1.0)
        phi = _safe_float(phi, 0.0)

        reinforcement = dict(reinforcement or {})
        goal_suggestions = list(goal_suggestions or [])

        learning_rate = _clamp(
            _safe_float(reinforcement.get("learning_rate", 0.1), 0.1),
            0.0,
            1.0,
        )
        stability_factor = _clamp(
            _safe_float(reinforcement.get("stability_factor", 1.0), 1.0),
            0.5,
            2.0,
        )

        alignment_error = _clamp(abs(phi - self_awareness), 0.0, 1.0)

        updates: Dict[str, Any] = {
            "setup_confidence_weights": {
                "field_stability": _clamp(1.0 + (reward * 0.15), 0.0, 2.0),
                "field_drift_response": _clamp(1.0 + (drift * 0.25), 0.0, 2.0),
            },
            "stand_down_sensitivity": {
                "field_instability": _clamp(1.0 + (drift * 0.5) - (reward * 0.1), 0.5, 2.0),
                "awareness_misalignment": _clamp(1.0 + alignment_error, 0.5, 2.0),
            },
            "llm_trust_weights": {
                "field_reasoner": _clamp(1.0 + ((coherence - drift) * 0.2), 0.0, 2.0),
                "reinforcement_signal": _clamp(1.0 + ((stability_factor - 1.0) * 0.3), 0.0, 2.0),
            },
            "event_caution_multipliers": {
                "field_anomaly": _clamp(1.0 + (drift * 0.4), 0.5, 3.0),
            },
        }

        # Goal-conditioned shaping
        if "reduce_drift" in goal_suggestions:
            updates["setup_confidence_weights"]["field_drift_response"] = _clamp(
                updates["setup_confidence_weights"]["field_drift_response"] + 0.1,
                0.0,
                2.0,
            )

        if "increase_coherence" in goal_suggestions:
            updates["setup_confidence_weights"]["field_stability"] = _clamp(
                updates["setup_confidence_weights"]["field_stability"] + 0.1,
                0.0,
                2.0,
            )

        if "restore_global_coherence" in goal_suggestions:
            updates["llm_trust_weights"]["field_reasoner"] = _clamp(
                updates["llm_trust_weights"]["field_reasoner"] + 0.05,
                0.0,
                2.0,
            )

        if "increase_self_awareness" in goal_suggestions:
            updates["stand_down_sensitivity"]["awareness_misalignment"] = _clamp(
                updates["stand_down_sensitivity"]["awareness_misalignment"] + 0.1,
                0.5,
                2.0,
            )

        confidence = _clamp((coherence + max(0.0, reward)) * 0.5, 0.0, 1.0)

        metadata: Dict[str, Any] = {
            "adapter": "field_decision_influence_adapter",
            "adapter_version": "v1",
            "emotion": emotion,
            "coherence": coherence,
            "delta_phi": dphi,
            "drift": drift,
            "reward": reward,
            "self_awareness": self_awareness,
            "phi": phi,
            "alignment_error": alignment_error,
            "goal_suggestions": goal_suggestions,
            "learning_rate": learning_rate,
            "stability_factor": stability_factor,
            "generated_at_unix": time.time(),
        }

        if extra_metadata:
            for k, v in extra_metadata.items():
                if k not in metadata:
                    metadata[k] = v

        update = DecisionInfluenceUpdate(
            session_id=str(session_id).strip(),
            turn_id=str(turn_id or f"turn-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}").strip(),
            source=str(source).strip() or FieldDecisionInfluenceAdapter.DEFAULT_SOURCE,
            reason=str(reason).strip() or FieldDecisionInfluenceAdapter.DEFAULT_REASON,
            updates=updates,
            confidence=confidence,
            metadata=metadata,
        )
        return update.validate()

    @staticmethod
    def build_from_hexcore_state(
        *,
        hexcore_id: str,
        coherence: float,
        dphi: float,
        reward: float,
        self_awareness: float,
        phi: float,
        goal_suggestions: Optional[List[str]] = None,
        reinforcement: Optional[Dict[str, Any]] = None,
        emotion: str = "neutral",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionInfluenceUpdate:
        """
        Convenience wrapper for HexCore callers.
        """
        return FieldDecisionInfluenceAdapter.build_update(
            session_id=hexcore_id,
            reward=reward,
            coherence=coherence,
            dphi=dphi,
            self_awareness=self_awareness,
            phi=phi,
            goal_suggestions=goal_suggestions,
            reinforcement=reinforcement,
            emotion=emotion,
            extra_metadata=extra_metadata,
        )


def build_field_decision_influence_update(
    *,
    session_id: str,
    reward: float,
    coherence: float,
    dphi: float,
    self_awareness: float = 0.5,
    phi: float = 0.0,
    goal_suggestions: Optional[List[str]] = None,
    reinforcement: Optional[Dict[str, Any]] = None,
    emotion: str = "neutral",
    turn_id: Optional[str] = None,
    source: str = FieldDecisionInfluenceAdapter.DEFAULT_SOURCE,
    reason: str = FieldDecisionInfluenceAdapter.DEFAULT_REASON,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> DecisionInfluenceUpdate:
    """
    Thin functional wrapper so HexCore can simply call:

        update = build_field_decision_influence_update(...)

    """
    return FieldDecisionInfluenceAdapter.build_update(
        session_id=session_id,
        reward=reward,
        coherence=coherence,
        dphi=dphi,
        self_awareness=self_awareness,
        phi=phi,
        goal_suggestions=goal_suggestions,
        reinforcement=reinforcement,
        emotion=emotion,
        turn_id=turn_id,
        source=source,
        reason=reason,
        extra_metadata=extra_metadata,
    )