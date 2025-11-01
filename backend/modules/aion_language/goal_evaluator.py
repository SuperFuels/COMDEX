"""
Goal Evaluator - Phase 42B
--------------------------
Evaluates recently created goals for success, partial progress, or failure
based on resonance feedback (drift, SRI, and variance stability).
"""

import time, json, math
from pathlib import Path
from backend.modules.aion_photon.goal_engine import GOALS
from backend.modules.aion_language.resonant_forecaster import RFE
from backend.modules.aion_language.resonant_drift_monitor import RDM
from backend.modules.aion_language.temporal_harmonics_monitor import THM

EVAL_PATH = Path("data/analysis/goal_evaluations.json")

class GoalEvaluator:
    def __init__(self):
        self.history = []

    def evaluate(self):
        """Iterate over current goals and mark their success state."""
        if not hasattr(GOALS, "goals") or not GOALS.goals:
            return None

        results = []
        sri = getattr(RFE.last_forecast or {}, "sri", None)
        drift = (getattr(RDM, "last_drift", {}) or {}).get("magnitude", 0)
        var = (getattr(THM, "last_harmonics", {}) or {}).get("variance", 0)

        for goal in GOALS.goals:
            if goal["status"] != "active":
                continue

            score = self._compute_score(sri, drift, var)
            if score > 0.7:
                status = "satisfied"
            elif score < 0.3:
                status = "failed"
            else:
                status = "in_progress"

            goal["status"] = status
            goal["confidence"] = round(score, 3)
            goal["evaluated_at"] = time.time()
            results.append(goal)
            print(f"[GoalEvaluator] 🧩 {goal['name']} -> {status} ({score:.2f})")

        self.history.extend(results)
        self._save()
        return results

    def _compute_score(self, sri, drift, var):
        """Combine metrics into a 0-1 success score (inverse risk)."""
        if sri is None:
            sri = 0.5
        # Low SRI, low drift, low variance = high success
        score = 1 - (0.5*sri + 0.3*drift + 0.2*var)
        return max(0, min(1, score))

    def _save(self):
        EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EVAL_PATH, "w") as f:
            json.dump(self.history[-50:], f, indent=2)

# Global instance
try:
    EVAL
except NameError:
    EVAL = GoalEvaluator()
    print("🧩 GoalEvaluator global instance initialized as EVAL")