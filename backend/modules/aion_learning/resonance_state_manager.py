#!/usr/bin/env python3
"""
Resonance State Manager
────────────────────────
Handles persistence for Gradient Correction Layer (GCL) state.
Stores running averages of resonance deltas and decay factors.

Path: data/predictive/resonance_state.json
"""

import json, time
from pathlib import Path

STATE_PATH = Path("data/predictive/resonance_state.json")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_STATE = {
    "avg_strength": 0.0,
    "decay_rate": 0.98,
    "update_count": 0,
    "timestamp": None,
}


class ResonanceStateManager:
    def __init__(self):
        self.state = DEFAULT_STATE.copy()
        self.load()

    # ─────────────────────────────────────────────
    # Load & Save
    # ─────────────────────────────────────────────
    def load(self):
        if STATE_PATH.exists():
            try:
                with open(STATE_PATH, "r") as f:
                    self.state = json.load(f)
            except Exception:
                print("⚠️ Corrupt resonance_state.json — using defaults.")
                self.state = DEFAULT_STATE.copy()

    def save(self):
        self.state["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(STATE_PATH, "w") as f:
            json.dump(self.state, f, indent=2)

    # ─────────────────────────────────────────────
    # Update Helpers
    # ─────────────────────────────────────────────
    def update(self, avg_strength: float, decay_rate: float):
        self.state["avg_strength"] = avg_strength
        self.state["decay_rate"] = decay_rate
        self.state["update_count"] += 1
        self.save()