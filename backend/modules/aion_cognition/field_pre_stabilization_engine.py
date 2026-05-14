"""
🧭  Field Pre-Stabilization Engine - Phase 53
---------------------------------------------
Stabilizes resonance forecast fields (ρ, Ī, SQI) before Codex fusion.

Inputs :
    data/telemetry/forecast_field.qdata.json
Outputs:
    data/telemetry/field_pre_stabilizer_state.json
"""

import json, time, math, logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

FORECAST = Path("data/telemetry/forecast_field.qdata.json")
STABIL_OUT = Path("data/telemetry/field_pre_stabilizer_state.json")


#───────────────────────────────────────────────
# 🌊  Stabilization Core
#───────────────────────────────────────────────
def pre_stabilization_cycle() -> Dict[str, Any]:
    """Smooth and stabilize forecasted resonance fields prior to Codex fusion."""
    if not FORECAST.exists():
        logger.warning("[Pre-Stabilizer] Missing forecast input.")
        return {}

    forecast = json.load(open(FORECAST))
    rho = forecast.get("ρ_next", 0.0)
    I = forecast.get("Ī_next", 0.0)
    sqi = forecast.get("SQI_next", 0.0)
    conf = forecast.get("confidence", 0.8)
    harmonic_strength = forecast.get("harmonic_strength", 0.0)

    # Adaptive smoothing factor: more stable for high confidence
    alpha = max(0.2, min(0.8, 1 - conf * 0.5))
    harmonic_gain = 1 + harmonic_strength * 0.1

    # Exponential smoothing with harmonic modulation
    ρ_stable = round((1 - alpha) * rho + alpha * (I * harmonic_gain), 6)
    Ī_stable = round((1 - alpha) * I + alpha * (sqi * harmonic_gain), 6)
    SQI_stable = round((1 - alpha) * sqi + alpha * ((rho + I) / 2 * harmonic_gain), 6)

    stabilized = {
        "timestamp": time.time(),
        "ρ_stable": ρ_stable,
        "Ī_stable": Ī_stable,
        "SQI_stable": SQI_stable,
        "alpha_used": alpha,
        "harmonic_gain": harmonic_gain,
        "confidence": conf,
        "schema": "FieldPreStabilizer.v1",
    }

    STABIL_OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(stabilized, open(STABIL_OUT, "w"), indent=2)
    logger.info(
        f"[Pre-Stabilizer] Exported stabilized field -> {STABIL_OUT} | "
        f"ρ={ρ_stable}, Ī={Ī_stable}, SQI={SQI_stable}, α={alpha}"
    )
    return stabilized


#───────────────────────────────────────────────
# 🚀  Entry Point
#───────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pre_stabilization_cycle()