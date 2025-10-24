# ================================================================
# 🔄 CEE Math Progression — Resonance Pattern Sequencer
# ================================================================
"""
Generates adaptive sequences of math exercises whose resonance
values evolve across time.  Tracks Δρ, ΔI, ΔSQI between successive
items to form a progression trajectory usable by GHX / CodexMetrics.

Outputs:
    data/learning/mathfield_progression_v1.qdata.json
"""

import json, time, logging
from pathlib import Path
from dataclasses import asdict
from statistics import mean

from backend.modules.aion_cognition.cee_math_templates import (
    generate_equation_match,
    generate_symbol_fill,
)
from backend.modules.aion_cognition.cee_math_schema import MathExercise

logger = logging.getLogger(__name__)
OUT_PATH = Path("data/learning/mathfield_progression_v1.qdata.json")

# ----------------------------------------------------------------------
def generate_progressive_sequence(n: int = 10):
    """Generate a sequence with resonance adaptation."""
    seq = []
    prev = None
    for i in range(n):
        func = generate_equation_match if i % 2 == 0 else generate_symbol_fill
        ex = func()

        if prev:
            ex.resonance["Δρ"] = round(ex.resonance["ρ"] - prev.resonance["ρ"], 3)
            ex.resonance["ΔI"] = round(ex.resonance["I"] - prev.resonance["I"], 3)
            ex.resonance["ΔSQI"] = round(ex.resonance["SQI"] - prev.resonance["SQI"], 3)
            # Adaptive difficulty tag
            trend = "up" if ex.resonance["ΔSQI"] > 0 else "down"
            ex.meta["difficulty_adaptive"] = (
                "harder" if trend == "up" else "easier"
            )
        else:
            ex.resonance.update({"Δρ": 0, "ΔI": 0, "ΔSQI": 0})
            ex.meta["difficulty_adaptive"] = "baseline"

        seq.append(ex)
        prev = ex
    return seq

# ----------------------------------------------------------------------
def export_progression():
    """Export the adaptive resonance progression dataset."""
    seq = generate_progressive_sequence(12)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump([asdict(e) for e in seq], open(OUT_PATH, "w"), indent=2)

    ρ_vals = [e.resonance["ρ"] for e in seq]
    I_vals = [e.resonance["I"] for e in seq]
    SQI_vals = [e.resonance["SQI"] for e in seq]
    summary = {
        "ρ̄": round(mean(ρ_vals), 3),
        "Ī": round(mean(I_vals), 3),
        "SQĪ": round(mean(SQI_vals), 3),
        "trend": "increasing" if SQI_vals[-1] > SQI_vals[0] else "decreasing",
        "schema": "MathFieldProgression.v1",
        "timestamp": time.time(),
    }
    logger.info(f"[CEE-MathProgression] Exported progression → {OUT_PATH}")
    print(json.dumps(summary, indent=2))
    return summary

# ----------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    export_progression()