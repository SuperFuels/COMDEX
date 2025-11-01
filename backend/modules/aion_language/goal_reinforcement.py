"""
Goal Reinforcement Engine - Phase 42C
-------------------------------------
Learns from goal evaluation outcomes to adjust Aion's internal motivation weights.
Successful goals strengthen resonance and confidence weighting,
failed goals reduce them or trigger adaptive recalibration.

Author: Tessaris Research Group
Date: Phase 42C - October 2025
"""

import time, json, math, logging
from pathlib import Path
from statistics import mean

from backend.modules.aion_photon.goal_engine import GOALS
from backend.modules.aion_language.goal_evaluator import EVAL
from backend.modules.aion_language.harmonic_memory_profile import HMP

logger = logging.getLogger(__name__)
REINF_PATH = Path("data/analysis/goal_reinforcement.json")

class GoalReinforcementEngine:
    def __init__(self):
        self.weights = {}   # {goal_name: weight}
        self.history = []
        self.learning_rate = 0.1
        self.stability_factor = 1.0
        print("🔁 GoalReinforcementEngine global instance initialized as REINF")

    def reinforce(self):
        """Scan recent goal evaluations and update internal goal weights."""
        if not EVAL.history:
            logger.warning("[Reinforcement] No evaluation data available.")
            return None

        latest_batch = EVAL.history[-5:]
        logger.info(f"[Reinforcement] Evaluating {len(latest_batch)} recent outcomes...")

        for g in latest_batch:
            name = g.get("name")
            conf = g.get("confidence", 0.5)
            status = g.get("status")

            if not name:
                continue

            # Base weight update
            delta = self.learning_rate * ((conf - 0.5) * 2)
            old_weight = self.weights.get(name, 0.5)

            # Adaptive logic
            if status == "satisfied":
                new_weight = min(1.0, old_weight + abs(delta))
            elif status == "failed":
                new_weight = max(0.0, old_weight - abs(delta))
            else:
                new_weight = old_weight * 0.98  # mild decay for partial

            self.weights[name] = round(new_weight, 3)
            self._log_reinforcement(name, status, old_weight, new_weight)

            # Optionally feed reinforcement data into harmonic memory
            HMP.log_entry({
                "goal": name,
                "old_weight": old_weight,
                "new_weight": new_weight,
                "confidence": conf,
                "status": status,
                "timestamp": time.time()
            })

        self._save()
        return self.weights

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
            self.learning_rate = learning_rate
            self.stability_factor = stability_factor

        # --------------------------------------------
        # Case 2 - calibration from motivation (Phase 45C)
        # --------------------------------------------
        elif stability_factor is not None or drift_factor is not None:
            stability_factor = max(0.0, min(stability_factor or 1.0, 2.0))
            drift_factor = max(0.0, min(drift_factor or 0.0, 1.0))
            self.learning_rate = round(0.1 + (stability_factor * 0.05), 3)
            self.stability_factor = round(max(0.5, 1.0 - drift_factor), 3)

        # --------------------------------------------
        # Default fallback - no external signal
        # --------------------------------------------
        else:
            self.learning_rate = getattr(self, "learning_rate", 0.1)
            self.stability_factor = getattr(self, "stability_factor", 1.0)

        print(
            f"[REINF] 🔧 Reinforcement parameters updated -> "
            f"learning_rate={self.learning_rate}, stability_factor={self.stability_factor}"
        )

        return {
            "learning_rate": self.learning_rate,
            "stability_factor": self.stability_factor,
        }

    def _log_reinforcement(self, goal, status, old, new):
        logger.info(f"[Reinforcement] 🔁 {goal}: {status} ({old:.2f} -> {new:.2f})")
        self.history.append({
            "goal": goal,
            "status": status,
            "old_weight": old,
            "new_weight": new,
            "timestamp": time.time()
        })

    def _save(self):
        REINF_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REINF_PATH, "w") as f:
            json.dump(self.history[-100:], f, indent=2)

# Global instance
try:
    REINF
except NameError:
    REINF = GoalReinforcementEngine()
    print("🔁 GoalReinforcementEngine global instance initialized as REINF")