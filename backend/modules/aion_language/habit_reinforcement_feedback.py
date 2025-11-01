"""
Habit Reinforcement Feedback - Phase 45E
----------------------------------------
Closes the Habit Encoding -> Motivation -> Reinforcement feedback loop.
Allows Aion to actively strengthen or weaken learned habits based on
emotional tone stability, motivational persistence, and reasoning performance.

This module represents Aion's first form of meta-learning - habits evolve
dynamically rather than accumulating statically over time.

Author: Tessaris Research Group
Date: Phase 45E - October 2025
"""

import time, json
from pathlib import Path

# Core subsystem imports
from backend.modules.aion_language.habit_encoding_engine import HABIT
from backend.modules.aion_language.temporal_motivation_persistence import MOTIVE
from backend.modules.aion_language.goal_reinforcement import REINF


class HabitReinforcementFeedback:
    def __init__(self):
        self.path = Path("data/motivation/habit_feedback.json")
        self.history = []
        print("🧩 HabitReinforcementFeedback global instance initialized as FEED")

    # ----------------------------------------------------
    # Core Feedback Logic
    # ----------------------------------------------------
    def run_feedback_cycle(self):
        """
        Perform one reinforcement feedback iteration based on recent motivational persistence
        and the current encoded habit profile.
        """

        # 🔹 Retrieve current habit records
        habits = HABIT.get_all_habits() if hasattr(HABIT, "get_all_habits") else {}
        if not habits:
            print("[FEED] ⚠️ No habit data available for feedback.")
            return None

        # 🔹 Retrieve motivational persistence metrics
        persistence_index = getattr(MOTIVE, "last_persistence", 0.8)
        avg_stability = getattr(MOTIVE, "avg_stability", 0.9)
        drift = getattr(MOTIVE, "avg_drift", 0.1)

        # 🔹 Determine most active (dominant) habit tone
        dominant_tone = max(habits.keys(), key=lambda t: habits[t].get("weight", 1.0))

        # 🔹 Compute reinforcement delta based on persistence and drift
        delta = round((persistence_index * 0.1) - (drift * 0.05), 3)
        delta = max(min(delta, 0.1), -0.1)  # clamp to ±0.1

        # 🔹 Reinforce the selected habit
        HABIT.reinforce_habit(dominant_tone, delta)

        # 🔹 Update global reinforcement engine parameters
        REINF.update_parameters(
            learning_rate=round(0.1 + delta, 3),
            stability_factor=round(avg_stability, 2)
        )

        # 🔹 Compose and log feedback entry
        feedback = {
            "timestamp": time.time(),
            "tone": dominant_tone,
            "delta": delta,
            "persistence_index": persistence_index,
            "avg_stability": avg_stability,
            "avg_drift": drift
        }

        self.history.append(feedback)
        self._save()
        self._log(feedback)
        return feedback

    # ----------------------------------------------------
    # Persistence
    # ----------------------------------------------------
    def _save(self):
        """Save last 50 feedback cycles."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.history[-50:], f, indent=2)

    def _log(self, feedback):
        """Human-readable feedback event summary."""
        tone = feedback["tone"]
        delta = feedback["delta"]
        if delta > 0:
            msg = f"[FEED] 🔄 Reinforced habit ({tone}) -> Δw=+{delta}"
        elif delta < 0:
            msg = f"[FEED] 🔻 Weakened habit ({tone}) -> Δw={delta}"
        else:
            msg = f"[FEED] ⚖️ No net change for habit ({tone})"
        print(msg)


# 🔄 Global instance
try:
    FEED
except NameError:
    FEED = HabitReinforcementFeedback()