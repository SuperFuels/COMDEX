"""
🔁  Quantum Motivator Feedback Loop  (Phase 46C)
──────────────────────────────────────────────────────
Integrates Aion emotional tone and motivational bias with QQC resonance feedback.

Responsibilities:
 * Receive QQC feedback (Δ⊕, Δ↔, Δ⟲)
 * Adjust tone, intent-bias, and exploration depth
 * Export motivfield.qdata.json for longitudinal tracking
"""

import json, logging, time, math, random
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)
OUT_PATH = Path("data/telemetry/motivfield.qdata.json")

#───────────────────────────────────────────────
# Core Motivator Cycle
#───────────────────────────────────────────────
def motivator_cycle(qqc_feedback: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process resonance deltas from QQC -> adjust motivational tone and bias.
    """
    Δ⊕ = qqc_feedback.get("Δ⊕", 0.0)
    Δ↔ = qqc_feedback.get("Δ↔", 0.0)
    Δ⟲ = qqc_feedback.get("Δ⟲", 0.0)

    # Compute derived parameters
    tone_shift = (Δ⊕ - Δ⟲) * 5.0
    depth_gain = 1.0 + (Δ↔ * 3.0)
    exploration_factor = max(0.05, min(0.2, abs(Δ⟲) + 0.05))

    tone = round(0.1 + tone_shift, 3)
    depth = round(0.9 * depth_gain, 3)
    exploration = round(exploration_factor, 3)

    motiv_state = {
        "timestamp": time.time(),
        "tone": tone,
        "depth": depth,
        "exploration": exploration,
        "schema": "MotivField.v1",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(motiv_state, open(OUT_PATH, "w"), indent=2)
    logger.info(
        f"[MotivLoop] tone={tone}, depth={depth}, exploration={exploration} -> exported -> {OUT_PATH}"
    )
    return motiv_state


#───────────────────────────────────────────────
# Self-Test
#───────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dummy_feedback = {"Δ⊕": -0.0042, "Δ↔": 0.0018, "Δ⟲": -0.0091}
    result = motivator_cycle(dummy_feedback)
    print(json.dumps(result, indent=2))