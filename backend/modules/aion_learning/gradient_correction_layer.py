#!/usr/bin/env python3
"""
AION Phase 32 — Gradient Correction Layer (Resonant Reinforcement)
──────────────────────────────────────────────────────────────────
Compares predicted vs. actual temporal feature vectors to compute
resonance deltas and emit corrective gradients back to PredictiveBias
and SQI engines.
"""

import json, math, time
from pathlib import Path
from typing import Dict, List
import numpy as np
from backend.modules.aion_learning.resonance_state_manager import ResonanceStateManager
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry

# ─────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────
DATA_DIR = Path("data/analysis")
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESONANCE_LOG = DATA_DIR / "resonance_delta.jsonl"


class GradientCorrectionLayer:
    def __init__(self, decay_rate: float = 0.98):
        self.decay_rate = decay_rate
        self.last_delta = 0.0
        self.avg_strength = 0.0
        self.state_mgr = ResonanceStateManager()
        self.avg_strength = self.state_mgr.state.get("avg_strength", 0.0)
        self.decay_rate = self.state_mgr.state.get("decay_rate", 0.98)
        self.update_counter = 0
        self.save_interval = 25  # only persist every 25 reinforcement updates
        self.telemetry = ResonanceTelemetry()

    # ─────────────────────────────────────────────
    # Compute vector difference (pred vs actual)
    # ─────────────────────────────────────────────
    def compute_delta(self, predicted_vec: List[float], actual_vec: List[float]) -> float:
        """Return normalized delta magnitude between predicted and actual vectors."""
        if not predicted_vec or not actual_vec:
            return 0.0
        p, a = np.array(predicted_vec), np.array(actual_vec)
        delta = float(np.linalg.norm(p - a))
        self.last_delta = delta
        self.avg_strength = self.avg_strength * self.decay_rate + delta * (1 - self.decay_rate)
        return delta

    # ─────────────────────────────────────────────
    # Reinforcement signal generation
    # ─────────────────────────────────────────────
    def compute_resonance_feedback(self, delta: float) -> float:
        """Map delta magnitude → reinforcement scalar in [−1, 1]."""
        if delta == 0:
            return 1.0
        r = max(-1.0, min(1.0, 1.0 - math.tanh(delta)))
        return r

    # ─────────────────────────────────────────────
    # Logging utility
    # ─────────────────────────────────────────────
    def log_delta(self, predicted_vec, actual_vec, delta, reward):
        entry = {
            "timestamp": time.time(),
            "delta": delta,
            "reward": reward,
            "predicted_vec": predicted_vec,
            "actual_vec": actual_vec,
        }
        with open(RESONANCE_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ─────────────────────────────────────────────
    # Main API call
    # ─────────────────────────────────────────────
    def reinforce(self, predicted_vec, actual_vec) -> float:
        """Compute resonance delta and return reinforcement scalar."""
        delta = self.compute_delta(predicted_vec, actual_vec)
        reward = self.compute_resonance_feedback(delta)
        self.log_delta(predicted_vec, actual_vec, delta, reward)

        # ─────────────────────────────────────────────
        # Persist resonance learning memory periodically
        # ─────────────────────────────────────────────
        self.update_counter += 1
        if self.update_counter % self.save_interval == 0:
            self.state_mgr.update(self.avg_strength, self.decay_rate)
            self.update_counter = 0  # reset

        # ─────────────────────────────────────────────
        # Emit telemetry update (GHX bridge feed)
        # ─────────────────────────────────────────────
        packet = self.telemetry.emit()
        packet["data"].update({
            "avg_strength": round(self.avg_strength, 6),
            "decay_rate": round(self.decay_rate, 4),
            "update_counter": self.update_counter
        })
        # Optional: print or log packet for debugging
        # print("📡 ResonanceTelemetry:", packet)

        return reward