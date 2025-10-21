"""
Tessaris AION Harmonic Learning & Stability Optimizer (HLSO)
Phase 6B — Adaptive Gain Tuning Layer
------------------------------------------------------------
Observes resonance_feedback.jsonl from the Resonant Coupling Interface (RCI)
and adjusts COUPLING_GAIN coefficients dynamically based on stability trends.

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import json
import os
import logging
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# Link to Resonant Coupling Interface constants
from backend.modules.aion_resonance import resonant_coupling_interface as rci

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DATA_PATH = Path("data/resonance_feedback.jsonl")
LEARNING_RATE = 0.05        # learning step size
WINDOW = 25                 # number of recent events to consider
STABILITY_TARGET = 0.985    # desired average stability

# ==========================================================
# 📊 Utility: Load and Smooth Stability Data
# ==========================================================

def load_recent_feedback(window: int = WINDOW):
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r") as f:
        lines = f.readlines()[-window:]
    feedback = []
    for line in lines:
        try:
            feedback.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return feedback


def compute_stability_stats(feedback):
    if not feedback:
        return None
    stabilities = [f.get("stability", 1.0) for f in feedback]
    mean_stab = float(np.mean(stabilities))
    var_stab = float(np.var(stabilities))
    return {"mean": mean_stab, "variance": var_stab}


# ==========================================================
# 🧠 Adaptive Gain Optimizer
# ==========================================================

def adjust_coupling_gains():
    feedback = load_recent_feedback(WINDOW)
    stats = compute_stability_stats(feedback)
    if not stats:
        logger.info("No stability data available — skipping optimization.")
        return rci.COUPLING_GAIN

    mean_stab = stats["mean"]
    delta = STABILITY_TARGET - mean_stab

    # Adjust each gain proportional to delta and recent variance
    variance_factor = 1.0 + stats["variance"] * 2.5
    for key in rci.COUPLING_GAIN:
        direction = np.sign(delta)
        adjust = LEARNING_RATE * direction / variance_factor
        rci.COUPLING_GAIN[key] += adjust
        rci.COUPLING_GAIN[key] = float(np.clip(rci.COUPLING_GAIN[key], -1.0, 1.0))

    logger.info(f"🧩 Stability mean={mean_stab:.4f} var={stats['variance']:.4f}")
    logger.info(f"🔧 Updated COUPLING_GAIN → {rci.COUPLING_GAIN}")

    # Persist the updated parameters
    save_path = Path("data/coupling_gain_state.json")
    with open(save_path, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mean_stability": mean_stab,
                "variance": stats["variance"],
                "coupling_gain": rci.COUPLING_GAIN,
            },
            f,
            indent=2,
        )

    return rci.COUPLING_GAIN


# ==========================================================
# 🚀 Autonomous Run Mode
# ==========================================================

if __name__ == "__main__":
    logger.info("🌌 Starting Harmonic Learning & Stability Optimizer...")
    updated_gains = adjust_coupling_gains()
    logger.info(f"✅ Optimization complete. New gains: {updated_gains}")