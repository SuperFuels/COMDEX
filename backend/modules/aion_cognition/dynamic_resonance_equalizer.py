"""
🎛  Dynamic Resonance Equalizer - Phase 50
-----------------------------------------
Continuously learns from Symatic Drift reports and applies adaptive tuning
to LexMemory decay rates, resonance weights, and field coherence.

Inputs :
    data/telemetry/symatic_drift_report.json
    data/telemetry/language_habit_metrics.json
Outputs:
    data/telemetry/resonance_equalizer_state.json
"""

import json, time, logging, math
from pathlib import Path

logger = logging.getLogger(__name__)

DRIFT_PATH = Path("data/telemetry/symatic_drift_report.json")
HABIT_PATH = Path("data/telemetry/language_habit_metrics.json")
OUT_PATH   = Path("data/telemetry/resonance_equalizer_state.json")

def _safe_load(path: Path) -> dict:
    if path.exists():
        with open(path) as f: 
            return json.load(f)
    return {}

def compute_equalizer(drift: dict, habit: dict) -> dict:
    """Compute adaptive adjustments to resonance decay and coherence."""
    ρ_corr = drift.get("ρ_corr", 0.0)
    Ī_corr = drift.get("Ī_corr", 0.0)
    SQI_corr = drift.get("SQI_corr", 0.0)
    stability = drift.get("stability", 1.0)
    habit_strength = habit.get("habit_strength", 0.0)

    # Learn adaptive decay tuning
    adaptive_decay = round(max(0.001, 0.02 * (1 - stability)), 5)
    coherence_gain = round(math.tanh(SQI_corr) * 0.5, 5)

    equalizer = {
        "timestamp": time.time(),
        "adaptive_decay": adaptive_decay,
        "coherence_gain": coherence_gain,
        "habit_coupling": round(habit_strength * ρ_corr, 5),
        "intensity_mod": round(Ī_corr * stability, 5),
        "SQI_target": round(SQI_corr, 5),
        "schema": "DynamicEqualizer.v1"
    }

    logger.info(
        f"[Equalizer] decay={adaptive_decay}, coherence_gain={coherence_gain}, SQI_target={SQI_corr}"
    )
    return equalizer

def update_equalizer_state():
    """Run self-training resonance equalizer."""
    drift = _safe_load(DRIFT_PATH)
    habit = _safe_load(HABIT_PATH)
    if not drift or not habit:
        logger.warning("[Equalizer] Missing data sources.")
        return None

    eq = compute_equalizer(drift, habit)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(eq, open(OUT_PATH, "w"), indent=2)
    logger.info(f"[Equalizer] Exported adaptive state -> {OUT_PATH}")
    return eq

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_equalizer_state()