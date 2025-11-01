"""
Habit Encoding Engine - Phase 45D v1.1
--------------------------------------
Consolidates persistent motivational and emotional cycles into
Habit Signatures. Enables Aion to retain long-term behavior patterns
and expose them for reinforcement feedback analysis.

Now synchronized with HabitReinforcementFeedback (Phase 45E):
 - unified habit store (`self.habits`)
 - consistent access via `get_all_habits()`

Author: Tessaris Research Group
Date: Phase 45D - October 2025
"""

import time, json
from pathlib import Path
from statistics import mean

from backend.modules.aion_language.goal_motivation_calibrator import CAL
from backend.modules.aion_language.temporal_motivation_persistence import MOTIVE
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.adaptive_reasoning_refiner import REASON


class HabitEncodingEngine:
    def __init__(self):
        # Unified in-memory habit store for feedback access
        self.habits = {}
        self.habit_log = Path("data/goals/habit_signatures.json")
        self.signatures = []
        self._load_existing()
        print("🧩 HabitEncodingEngine global instance initialized as HABIT")

    # ----------------------------------------------------
    # Data Persistence
    # ----------------------------------------------------
    def _load_existing(self):
        """Load persisted habits into memory."""
        if self.habit_log.exists():
            try:
                self.signatures = json.load(open(self.habit_log))
                # Rebuild habit cache from loaded signatures
                for h in self.signatures:
                    self.habits[h["tone"]] = h
            except Exception:
                self.signatures = []
                self.habits = {}

    def _save(self):
        """Persist recent habits to disk."""
        self.habit_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.habit_log, "w") as f:
            json.dump(self.signatures[-100:], f, indent=2)

    # ----------------------------------------------------
    # Core Encoding Logic
    # ----------------------------------------------------
    def encode(self):
        """Generate or reinforce a habit signature from current system state."""
        signature = {
            "timestamp": time.time(),
            "tone": TONE.state.get("tone", "neutral"),
            "confidence": TONE.state.get("confidence", 0.5),
            "energy": TONE.state.get("energy", 0.5),
            "bias_depth": getattr(REASON, "bias_state", {}).get("depth", 1.0),
            "bias_exploration": getattr(REASON, "bias_state", {}).get("exploration", 1.0),
            "learning_rate": getattr(MOTIVE, "current_lr", 0.1),
            "persistence": getattr(MOTIVE, "persistence_index", 0.5),
            "goal_focus": getattr(CAL, "last_focus", 0.5),
        }

        # Identify and reinforce matching tone-based habits
        reinforced = False
        for h in self.signatures:
            if (abs(h["persistence"] - signature["persistence"]) < 0.1
                    and h["tone"] == signature["tone"]):
                h["weight"] = round(h.get("weight", 1.0) + 0.1, 2)
                h["last_seen"] = signature["timestamp"]
                self.habits[h["tone"]] = h
                reinforced = True
                print(f"[HABIT] 🔁 Reinforced existing habit ({h['tone']}) -> weight={h['weight']}")
                break

        if not reinforced:
            signature["weight"] = 1.0
            signature["last_seen"] = signature["timestamp"]
            self.signatures.append(signature)
            self.habits[signature["tone"]] = signature
            print(f"[HABIT] 🌱 New habit encoded ({signature['tone']})")

        self._save()
        return signature

    # ----------------------------------------------------
    # Analytical Summaries
    # ----------------------------------------------------
    def summarize(self):
        """Return an overview of active habit clusters."""
        summary = {
            "total_habits": len(self.signatures),
            "dominant_tones": list({h["tone"] for h in self.signatures}),
            "avg_weight": round(mean([h.get("weight", 1.0) for h in self.signatures]), 2)
        }
        print(f"[HABIT] 📘 Summary: {summary}")
        return summary

    def get_all_habits(self):
        """Expose full habit map for reinforcement feedback."""
        if self.habits:
            return self.habits
        elif hasattr(self, "habit_memory") and self.habit_memory:
            return self.habit_memory
        else:
            print("[HABIT] ⚠️ No stored habits found.")
            return {}

    def reinforce_habit(self, tone: str, delta: float):
        """
        Reinforce or weaken a specific habit by tone label.

        Parameters:
            tone (str): tone associated with the habit (e.g. 'reflective', 'neutral')
            delta (float): reinforcement increment (+) or decrement (-)
        """
        if tone not in self.habits:
            print(f"[HABIT] ⚠️ No existing habit found for tone '{tone}'.")
            return None

        habit = self.habits[tone]
        old_weight = habit.get("weight", 1.0)
        habit["weight"] = round(max(0.1, old_weight + delta), 2)
        habit["last_seen"] = time.time()

        # Reflect change into persistent list
        for h in self.signatures:
            if h["tone"] == tone:
                h["weight"] = habit["weight"]
                h["last_seen"] = habit["last_seen"]
                break

        self._save()
        print(f"[HABIT] 🔄 Reinforcement update -> ({tone}) Δw={delta:+.3f} -> {habit['weight']}")
        return habit


# 🔄 Global instance
try:
    HABIT
except NameError:
    HABIT = HabitEncodingEngine()