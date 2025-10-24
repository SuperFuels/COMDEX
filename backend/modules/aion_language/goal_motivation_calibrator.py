"""
Motivational Resonance Calibration — Phase 45B
----------------------------------------------
Bridges Aion’s emotional + reasoning coherence with its motivational stability.
Calibrates goal persistence and reinforcement weights according to harmonic
resonance among tone, reasoning depth, and goal success.

Author: Tessaris Research Group
Date: Phase 45B — October 2025
"""

import time, json
from pathlib import Path

from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.adaptive_reasoning_refiner import REASON
from backend.modules.aion_photon.goal_engine import GOALS
from backend.modules.aion_language.goal_reinforcement import REINF

class GoalMotivationCalibrator:
    def __init__(self):
        self.log_path = Path("data/goals/motivation_resonance_log.json")
        self.last_state = {}

    # ───────────────────────────────────────────────
    def compute_motivation_resonance(self):
        """Compute motivational resonance from tone + reasoning bias."""
        tone_conf = TONE.state.get("confidence", 0.5)
        tone_energy = TONE.state.get("energy", 0.5)

        bias = getattr(REASON, "reasoning_bias", {})
        depth = bias.get("depth", 1.0)
        exploration = bias.get("exploration", 1.0)

        stability = round((tone_conf + depth) / 2, 3)
        focus = round((tone_energy + exploration) / 2, 3)
        drift = round(abs(stability - focus), 3)

        self.last_state = {
            "timestamp": time.time(),
            "stability": stability,
            "focus": focus,
            "drift": drift,
        }
        return self.last_state

    # ───────────────────────────────────────────────
    def calibrate_motivation(self):
        """Propagate resonance metrics into GoalEngine + Reinforcement layer."""
        state = self.compute_motivation_resonance()

        # Update GoalEngine internal state
        GOALS.motivation_resonance = {
            "stability": state["stability"],
            "focus": state["focus"],
            "drift": state["drift"],
        }

        # Adjust reinforcement parameters
        REINF.update_parameters(
            stability_factor=state["stability"],
            drift_factor=state["drift"]
        )

        # Persist to log
        self._save(state)

        print(
            f"[GOALS] 🎯 Calibrated motivational resonance "
            f"(stability={state['stability']}, drift={state['drift']})"
        )
        return state

    # ───────────────────────────────────────────────
    def _save(self, state):
        """Append calibration result to persistent log."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if self.log_path.exists():
            try:
                history = json.load(open(self.log_path))
            except Exception:
                history = []
        history.append(state)
        with open(self.log_path, "w") as f:
            json.dump(history[-100:], f, indent=2)

# 🔄 Global instance
try:
    CAL
except NameError:
    CAL = GoalMotivationCalibrator()
    print("🧭 GoalMotivationCalibrator global instance initialized as CAL")