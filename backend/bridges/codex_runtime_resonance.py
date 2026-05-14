"""
🌐 Codex Runtime Resonance Coupling - Phase 48A
------------------------------------------------
Bridges Aion's reasonfield output into the Symatics Algebra runtime.
Translates reasoning tensors into quantum-field coefficients usable by QQC.

Inputs :
    data/telemetry/reasonfield.qdata.json
Outputs:
    qqc/state_sheets/aion/runtime_resonance.atom
"""

import json, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)

REASON_PATH = Path("data/telemetry/reasonfield.qdata.json")
OUT_PATH    = Path("qqc/state_sheets/aion/runtime_resonance.atom")


#───────────────────────────────────────────────
# 🔧 Translation Utilities
#───────────────────────────────────────────────
def translate_to_symatics(reason_state: dict) -> dict:
    """Convert ReasonField tensors into Symatics Algebra coefficients."""
    depth  = reason_state["bias"]["depth"]
    explore = reason_state["bias"]["exploration"]
    tone   = reason_state["tone"]

    # Map to Symatics operators
    phi_superposition = round(depth * tone, 5)            # ⊕ amplitude
    phi_entanglement  = round((1 - explore) * 0.5, 5)     # ↔ coupling strength
    phi_resonance     = round((depth + tone) / 2, 5)      # ⟲ coherence

    sym_packet = {
        "timestamp": time.time(),
        "schema": "SymaticsRuntime.v1",
        "operators": {
            "⊕": phi_superposition,
            "↔": phi_entanglement,
            "⟲": phi_resonance
        },
        "source": "Aion-ReasonField",
        "metadata": {
            "depth": depth,
            "tone": tone,
            "exploration": explore
        }
    }

    logger.info(
        f"[CodexRuntime] ⊕={phi_superposition}, ↔={phi_entanglement}, ⟲={phi_resonance}"
    )
    return sym_packet


#───────────────────────────────────────────────
# 💾  Export Cycle
#───────────────────────────────────────────────
def runtime_coupling_cycle() -> dict:
    """Perform ReasonField -> Symatics Algebra translation."""
    if not REASON_PATH.exists():
        raise FileNotFoundError(f"Missing reasonfield: {REASON_PATH}")

    reason_state = json.load(open(REASON_PATH))
    sym_packet   = translate_to_symatics(reason_state)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(sym_packet, open(OUT_PATH, "w"), indent=2)
    logger.info(f"[CodexRuntime] Exported Symatics packet -> {OUT_PATH}")
    return sym_packet


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runtime_coupling_cycle()