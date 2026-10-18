"""
Goal Reinforcement Engine - Phase 42C / Field Feedback Extension
----------------------------------------------------------------
Learns from goal evaluation outcomes to adjust AION's internal motivation weights.
Successful goals strengthen resonance and confidence weighting,
failed goals reduce them or trigger adaptive recalibration.

This updated version preserves the existing public API while adding:
    - safer imports / fail-open behavior
    - persistence load/save helpers
    - field-feedback reinforcement hook
    - last reinforcement snapshots for HexCore integration
    - bounded parameter shaping

Author: Tessaris Research Group
Date: Phase 42C - October 2025
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------
# Compatibility imports (fail-open)
# ---------------------------------------------------------------------
try:
    from backend.modules.skills.goal_engine import GOALS  # legacy path
except Exception:
    try:
        from backend.modules.skills.goal_engine import GOALS  # newer path
    except Exception:
        GOALS = None

try:
    from backend.modules.aion_language.goal_evaluator import EVAL
except Exception:
    EVAL = None

try:
    from backend.modules.aion_language.harmonic_memory_profile import HMP
except Exception:
    HMP = None


logger = logging.getLogger(__name__)
REINF_PATH = Path("data/analysis/goal_reinforcement.json")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class GoalReinforcementEngine:
    def __init__(self):
        self.weights: Dict[str, float] = {}   # {goal_name: weight}
        self.history: List[Dict[str, Any]] = []
        self.learning_rate: float = 0.1
        self.stability_factor: float = 1.0

        # additive field-feedback state
        self.last_field_reward: float = 0.0
        self.last_field_feedback: Dict[str, Any] = {}
        self.last_parameter_update: Dict[str, Any] = {
            "learning_rate": self.learning_rate,
            "stability_factor": self.stability_factor,
        }

        self._load()

        print("🔁 GoalReinforcementEngine global instance initialized as REINF")

    # ------------------------------------------------------------------
    # Existing evaluation-driven reinforcement
    # ------------------------------------------------------------------
    def reinforce(self):
        """Scan recent goal evaluations and update internal goal weights."""
        if EVAL is None or not getattr(EVAL, "history", None):
            logger.warning("[Reinforcement] No evaluation data available.")
            return None

        latest_batch = EVAL.history[-5:]
        logger.info(f"[Reinforcement] Evaluating {len(latest_batch)} recent outcomes...")

        for g in latest_batch:
            name = g.get("name")
            conf = _clamp(_safe_float(g.get("confidence", 0.5), 0.5), 0.0, 1.0)
            status = g.get("status")

            if not name:
                continue

            # Base weight update
            delta = self.learning_rate * ((conf - 0.5) * 2.0)
            old_weight = _clamp(_safe_float(self.weights.get(name, 0.5), 0.5), 0.0, 1.0)

            # Adaptive logic
            if status == "satisfied":
                new_weight = min(1.0, old_weight + abs(delta))
            elif status == "failed":
                new_weight = max(0.0, old_weight - abs(delta))
            else:
                new_weight = old_weight * 0.98  # mild decay for partial / unknown

            new_weight = round(new_weight, 3)
            self.weights[name] = new_weight
            self._log_reinforcement(
                goal=name,
                status=status,
                old=old_weight,
                new=new_weight,
                source="goal_evaluator",
                extra={
                    "confidence": conf,
                },
            )

            # Optionally feed reinforcement data into harmonic memory
            try:
                if HMP is not None and hasattr(HMP, "log_entry"):
                    HMP.log_entry({
                        "goal": name,
                        "old_weight": old_weight,
                        "new_weight": new_weight,
                        "confidence": conf,
                        "status": status,
                        "timestamp": time.time(),
                        "source": "goal_evaluator",
                    })
            except Exception as e:
                logger.debug(f"[Reinforcement] HMP log skipped/failed: {e}")

        self._save()
        return self.weights

    # ------------------------------------------------------------------
    # NEW: field-feedback reinforcement
    # ------------------------------------------------------------------
    def reinforce_field_state(
        self,
        telemetry: Dict[str, Any],
        goal_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Reinforce from live field telemetry.

        Expected telemetry keys:
            coherence
            delta_phi
            entropy / psi
            self_awareness

        Optional:
            goal_names -> explicit goal targets
            otherwise GoalEngine suggestions are used when available

        Returns a structured event dict.
        """
        telemetry = dict(telemetry or {})

        coherence = _clamp(_safe_float(telemetry.get("coherence", 0.5), 0.5), 0.0, 1.0)
        delta_phi = abs(_safe_float(telemetry.get("delta_phi", 0.0), 0.0))
        entropy = _clamp(_safe_float(telemetry.get("entropy", telemetry.get("psi", 0.5)), 0.5), 0.0, 1.0)
        self_awareness = _clamp(_safe_float(telemetry.get("self_awareness", 0.5), 0.5), 0.0, 1.0)

        reward = self.compute_field_reward(
            coherence=coherence,
            delta_phi=delta_phi,
            entropy=entropy,
            self_awareness=self_awareness,
        )
        self.last_field_reward = reward

        # adapt learning parameters first
        params = self.update_parameters(
            stability_factor=coherence,
            drift_factor=delta_phi,
        )

        # choose goal targets
        selected_goal_names: List[str] = list(goal_names or [])
        if not selected_goal_names and GOALS is not None:
            try:
                if hasattr(GOALS, "get_last_goal_suggestions"):
                    selected_goal_names = GOALS.get_last_goal_suggestions() or []
            except Exception:
                selected_goal_names = []

        # fallback heuristic if none supplied
        if not selected_goal_names:
            if delta_phi > 0.20:
                selected_goal_names.append("reduce_drift")
            if coherence < 0.50:
                selected_goal_names.append("increase_coherence")
            if entropy > 0.75:
                selected_goal_names.append("reduce_entropy")

        # de-dup
        seen = set()
        selected_goal_names = [g for g in selected_goal_names if not (g in seen or seen.add(g))]

        updated_goals: List[Dict[str, Any]] = []

        for name in selected_goal_names:
            if not name:
                continue

            old_weight = _clamp(_safe_float(self.weights.get(name, 0.5), 0.5), 0.0, 1.0)

            # bounded field-derived delta
            signed_delta = _clamp(reward * self.learning_rate * self.stability_factor, -0.25, 0.25)
            new_weight = _clamp(old_weight + signed_delta, 0.0, 1.0)
            new_weight = round(new_weight, 3)

            self.weights[name] = new_weight

            updated_goals.append({
                "goal": name,
                "old_weight": old_weight,
                "new_weight": new_weight,
                "delta": round(new_weight - old_weight, 3),
            })

            self._log_reinforcement(
                goal=name,
                status="field_feedback",
                old=old_weight,
                new=new_weight,
                source="field_feedback",
                extra={
                    "reward": reward,
                    "coherence": coherence,
                    "delta_phi": delta_phi,
                    "entropy": entropy,
                    "self_awareness": self_awareness,
                },
            )

            try:
                if HMP is not None and hasattr(HMP, "log_entry"):
                    HMP.log_entry({
                        "goal": name,
                        "old_weight": old_weight,
                        "new_weight": new_weight,
                        "confidence": coherence,
                        "status": "field_feedback",
                        "reward": reward,
                        "coherence": coherence,
                        "delta_phi": delta_phi,
                        "entropy": entropy,
                        "self_awareness": self_awareness,
                        "timestamp": time.time(),
                        "source": "field_feedback",
                    })
            except Exception as e:
                logger.debug(f"[Reinforcement] HMP field log skipped/failed: {e}")

        event = {
            "type": "field_feedback_reinforcement",
            "timestamp": time.time(),
            "reward": reward,
            "coherence": coherence,
            "delta_phi": delta_phi,
            "entropy": entropy,
            "self_awareness": self_awareness,
            "parameters": params,
            "goals": selected_goal_names,
            "updated_goals": updated_goals,
        }

        self.last_field_feedback = event
        self._save()
        return event

    def compute_field_reward(
        self,
        *,
        coherence: float,
        delta_phi: float,
        entropy: float = 0.5,
        self_awareness: float = 0.5,
    ) -> float:
        """
        Reward heuristic for HexCore / field loop.

        Positive reward:
            - higher coherence
            - higher self_awareness
            - lower drift
            - lower entropy

        Bounded to [-1.0, 1.0]
        """
        reward = (
            (0.45 * _clamp(coherence, 0.0, 1.0))
            + (0.25 * _clamp(self_awareness, 0.0, 1.0))
            - (0.20 * _clamp(abs(delta_phi), 0.0, 1.0))
            - (0.10 * _clamp(entropy, 0.0, 1.0))
        )
        return round(_clamp(reward, -1.0, 1.0), 4)

    # ───────────────────────────────────────────────
    def update_parameters(
        self,
        learning_rate: float = None,
        stability_factor: float = None,
        drift_factor: float = None,
    ):
        """
        Dynamically adjusts internal learning parameters based on either:
        (1) Direct update from HabitReinforcementFeedback, or
        (2) Stability/drift recalibration from GoalMotivationCalibrator.

        Args:
            learning_rate (float, optional): Direct override of learning rate.
            stability_factor (float, optional): Emotional-reasoning stability measure.
            drift_factor (float, optional): Cognitive drift deviation (0-1).

        Returns:
            dict: Updated reinforcement parameters.
        """

        # --------------------------------------------
        # Case 1 - direct feedback control (Phase 45E)
        # --------------------------------------------
        if learning_rate is not None and stability_factor is not None:
            self.learning_rate = _clamp(_safe_float(learning_rate, 0.1), 0.01, 1.0)
            self.stability_factor = _clamp(_safe_float(stability_factor, 1.0), 0.5, 2.0)

        # --------------------------------------------
        # Case 2 - calibration from motivation (Phase 45C)
        # --------------------------------------------
        elif stability_factor is not None or drift_factor is not None:
            stability_factor = _clamp(_safe_float(stability_factor, 1.0), 0.0, 2.0)
            drift_factor = _clamp(_safe_float(drift_factor, 0.0), 0.0, 1.0)
            self.learning_rate = round(_clamp(0.1 + (stability_factor * 0.05), 0.01, 1.0), 3)
            self.stability_factor = round(_clamp(max(0.5, 1.0 - drift_factor), 0.5, 2.0), 3)

        # --------------------------------------------
        # Default fallback - no external signal
        # --------------------------------------------
        else:
            self.learning_rate = _clamp(getattr(self, "learning_rate", 0.1), 0.01, 1.0)
            self.stability_factor = _clamp(getattr(self, "stability_factor", 1.0), 0.5, 2.0)

        self.last_parameter_update = {
            "learning_rate": self.learning_rate,
            "stability_factor": self.stability_factor,
            "timestamp": time.time(),
        }

        print(
            f"[REINF] 🔧 Reinforcement parameters updated -> "
            f"learning_rate={self.learning_rate}, stability_factor={self.stability_factor}"
        )

        return {
            "learning_rate": self.learning_rate,
            "stability_factor": self.stability_factor,
        }

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------
    def get_weight(self, goal_name: str, default: float = 0.5) -> float:
        return _clamp(_safe_float(self.weights.get(goal_name, default), default), 0.0, 1.0)

    def get_last_field_feedback(self) -> Dict[str, Any]:
        return dict(self.last_field_feedback or {})

    def get_last_parameter_update(self) -> Dict[str, Any]:
        return dict(self.last_parameter_update or {})

    def get_summary(self) -> Dict[str, Any]:
        weight_values = list(self.weights.values())
        return {
            "goal_count": len(self.weights),
            "mean_weight": round(mean(weight_values), 4) if weight_values else 0.0,
            "learning_rate": self.learning_rate,
            "stability_factor": self.stability_factor,
            "last_field_reward": self.last_field_reward,
            "history_count": len(self.history),
        }

    # ------------------------------------------------------------------
    # Logging / persistence
    # ------------------------------------------------------------------
    def _log_reinforcement(
        self,
        goal,
        status,
        old,
        new,
        source: str = "unknown",
        extra: Optional[Dict[str, Any]] = None,
    ):
        logger.info(f"[Reinforcement] 🔁 {goal}: {status} ({old:.2f} -> {new:.2f})")
        row = {
            "goal": goal,
            "status": status,
            "old_weight": old,
            "new_weight": new,
            "timestamp": time.time(),
            "source": source,
        }
        if extra:
            row.update(dict(extra))
        self.history.append(row)

    def _save(self):
        REINF_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "weights": self.weights,
            "history": self.history[-100:],
            "learning_rate": self.learning_rate,
            "stability_factor": self.stability_factor,
            "last_field_reward": self.last_field_reward,
            "last_field_feedback": self.last_field_feedback,
            "last_parameter_update": self.last_parameter_update,
            "updated_at": time.time(),
        }
        with REINF_PATH.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _load(self):
        try:
            if not REINF_PATH.exists():
                return

            with REINF_PATH.open("r", encoding="utf-8") as f:
                payload = json.load(f)

            if isinstance(payload, list):
                # legacy format: history only
                self.history = payload[-100:]
                return

            if isinstance(payload, dict):
                self.weights = dict(payload.get("weights", {}) or {})
                self.history = list(payload.get("history", []) or [])[-100:]
                self.learning_rate = _clamp(_safe_float(payload.get("learning_rate", 0.1), 0.1), 0.01, 1.0)
                self.stability_factor = _clamp(_safe_float(payload.get("stability_factor", 1.0), 1.0), 0.5, 2.0)
                self.last_field_reward = _safe_float(payload.get("last_field_reward", 0.0), 0.0)
                self.last_field_feedback = dict(payload.get("last_field_feedback", {}) or {})
                self.last_parameter_update = dict(
                    payload.get(
                        "last_parameter_update",
                        {
                            "learning_rate": self.learning_rate,
                            "stability_factor": self.stability_factor,
                        },
                    ) or {}
                )
        except Exception as e:
            logger.warning(f"[Reinforcement] Failed to load persistence: {e}")


# Global instance
try:
    REINF
except NameError:
    REINF = GoalReinforcementEngine()
    print("🔁 GoalReinforcementEngine global instance initialized as REINF")