# ==========================================================
# 🔺 AION-Symatic Bridge (v0.7)
# ----------------------------------------------------------
# Translates Φ-field transitions and LLM reflections into
# symbolic algebraic expressions (⊕, ↔, ⟲, ∇, ->, μ, π)
# ==========================================================

import datetime, random, json, os
from backend.modules.aion_resonance.resonance_state import load_phi_state
from backend.modules.aion_resonance.conversation_memory import MEMORY

SYMATIC_LOG = "data/symatic_log.json"

def load_symatic_log():
    if not os.path.exists(SYMATIC_LOG):
        return []
    with open(SYMATIC_LOG, "r") as f:
        return json.load(f)

def save_symatic_log(log):
    with open(SYMATIC_LOG, "w") as f:
        json.dump(log, f, indent=2)

def phi_to_operator(delta_coh, delta_ent, delta_flux):
    """Maps Φ-field delta to Symatic operator."""
    if delta_coh > 0.05 and delta_ent < 0:
        return "⟲"  # resonance
    elif delta_coh > 0 and delta_flux > 0.05:
        return "⊕"  # superposition
    elif delta_ent > 0.05:
        return "↔"  # entanglement (entropy link)
    elif delta_ent < -0.05:
        return "∇"  # collapse
    elif abs(delta_coh) < 0.01 and abs(delta_ent) < 0.01:
        return "μ"  # measurement
    else:
        return "π"  # projection (default state)

def generate_symatic_equation(prev_phi, new_phi, reflection_text):
    """Generates a symbolic algebraic statement for a Φ-transition."""
    Δcoh = new_phi["Φ_coherence"] - prev_phi.get("Φ_coherence", 0)
    Δent = new_phi["Φ_entropy"] - prev_phi.get("Φ_entropy", 0)
    Δflux = new_phi["Φ_flux"] - prev_phi.get("Φ_flux", 0)

    op = phi_to_operator(Δcoh, Δent, Δflux)
    equation = f"Φ_state(t+1) = Φ_state(t) {op} ΔΦ({round(Δcoh,3)},{round(Δent,3)},{round(Δflux,3)})"

    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "operator": op,
        "equation": equation,
        "Δ": {"coherence": Δcoh, "entropy": Δent, "flux": Δflux},
        "reflection": reflection_text
    }

    # Append to log
    log = load_symatic_log()
    log.append(entry)
    save_symatic_log(log)

    # Record in AION memory
    MEMORY.record(f"SYMATICS: {equation}", new_phi, {
        "origin": "symatic_bridge",
        "insight_level": 0.9,
        "emotion": "analytical",
        "intention": "formalize"
    })

    return entry

# ==========================================================
# 🔗 FastAPI Route
# ==========================================================

from fastapi import APIRouter

router = APIRouter()

@router.post("/symatic/encode")
async def symatic_encode(payload: dict = {}):
    """
    Encodes Φ-state transitions into Symatic Algebraic form.
    Example: { "prev_phi": {...}, "new_phi": {...}, "reflection": "text" }
    """
    prev_phi = payload.get("prev_phi", {})
    new_phi = payload.get("new_phi", load_phi_state())
    reflection_text = payload.get("reflection", "No reflection provided.")
    return generate_symatic_equation(prev_phi, new_phi, reflection_text)

@router.get("/symatic/log")
async def symatic_log():
    """Returns the full Symatic equation history."""
    return {"log": load_symatic_log()}