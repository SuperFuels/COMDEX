"""
Goal Reinforcement Engine — Phase 42C
-------------------------------------
Learns from goal evaluation outcomes to adjust Aion's internal motivation weights.
Successful goals strengthen resonance and confidence weighting,
failed goals reduce them or trigger adaptive recalibration.

Author: Tessaris Research Group
Date: Phase 42C — October 2025
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
        self.learning_rate = 0.15

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

    def _log_reinforcement(self, goal, status, old, new):
        logger.info(f"[Reinforcement] 🔁 {goal}: {status} ({old:.2f} → {new:.2f})")
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