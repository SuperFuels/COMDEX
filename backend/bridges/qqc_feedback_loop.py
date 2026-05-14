"""
🌌  Live QQC Feedback Integration - Phase 48B
---------------------------------------------
Reads Aion's emitted Symatics packet (⊕, ↔, ⟲), simulates QQC resonance
adjustments (Δ⊕, Δ↔, Δ⟲), and applies adaptive corrections to ReasonField.

Inputs :
    qqc/state_sheets/aion/runtime_resonance.atom
Outputs:
    qqc/state_sheets/aion/feedback_return.atom
    data/telemetry/reasonfield.qdata.json (updated)
"""

import json, time, random, logging
from pathlib import Path

logger = logging.getLogger(__name__)

RUNTIME_PATH = Path("qqc/state_sheets/aion/runtime_resonance.atom")
RETURN_PATH  = Path("qqc/state_sheets/aion/feedback_return.atom")
REASON_PATH  = Path("data/telemetry/reasonfield.qdata.json")


#───────────────────────────────────────────────
# 🔭  Photonic Feedback Simulation
#───────────────────────────────────────────────
def simulate_feedback(sym_packet: dict) -> dict:
    """Generate photonic deltas to simulate QQC field feedback."""
    ops = sym_packet["operators"]
    d_superposition = round((random.random() - 0.5) * 0.02, 5)
    d_entanglement  = round((random.random() - 0.5) * 0.015, 5)
    d_resonance     = round((random.random() - 0.5) * 0.025, 5)

    feedback = {
        "timestamp": time.time(),
        "schema": "QQCFeedback.v1",
        "Δ⊕": d_superposition,
        "Δ↔": d_entanglement,
        "Δ⟲": d_resonance,
        "input": ops,
        "coherence_delta": round(sum([d_superposition, d_entanglement, d_resonance]) / 3, 5)
    }
    logger.info(
        f"[QQC-Feedback] Δ⊕={d_superposition}, Δ↔={d_entanglement}, Δ⟲={d_resonance}"
    )
    return feedback


#───────────────────────────────────────────────
# 🔄  Adaptive Assimilation
#───────────────────────────────────────────────
def apply_feedback_to_reasoner(feedback: dict):
    """Blend feedback deltas into the current ReasonField."""
    if not REASON_PATH.exists():
        logger.warning("[QQC-Feedback] No reasonfield found - skipping assimilation.")
        return

    data = json.load(open(REASON_PATH))
    d = feedback

    # Adjust tone/depth based on feedback deltas
    tone_new = round(max(0.0, data["tone"] + d["Δ⊕"]), 5)
    depth_new = round(max(0.0, data["bias"]["depth"] + d["Δ⟲"]), 5)

    data["tone"] = tone_new
    data["bias"]["depth"] = depth_new
    data["meta"]["feedback_timestamp"] = time.time()

    json.dump(data, open(REASON_PATH, "w"), indent=2)
    logger.info(f"[QQC-Feedback] Updated ReasonField tone={tone_new}, depth={depth_new}")


#───────────────────────────────────────────────
# 💾  Full Feedback Cycle
#───────────────────────────────────────────────
def qqc_feedback_cycle() -> dict:
    """Perform QQC feedback generation and adaptive correction."""
    if not RUNTIME_PATH.exists():
        raise FileNotFoundError(f"Missing Symatics packet: {RUNTIME_PATH}")

    sym_packet = json.load(open(RUNTIME_PATH))
    feedback   = simulate_feedback(sym_packet)

    RETURN_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(feedback, open(RETURN_PATH, "w"), indent=2)
    logger.info(f"[QQC-Feedback] Exported feedback -> {RETURN_PATH}")

    apply_feedback_to_reasoner(feedback)
    return feedback


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    qqc_feedback_cycle()