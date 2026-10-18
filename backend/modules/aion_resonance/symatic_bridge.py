# ==========================================================
# 🔺 AION-Symatic Bridge (v0.7)
# ----------------------------------------------------------
# Translates Φ-field transitions and LLM reflections into
# symbolic algebraic expressions (⊕, ↔, ⟲, ∇, ->, μ, π)
# ==========================================================

import datetime, random
from backend.modules.aion_resonance.resonance_state import load_phi_state
from backend.modules.aion_resonance.conversation_memory import MEMORY
from backend.modules.aion_resonance.symatic_event_store import (
    SYMATIC_EVENTS,
    SymaticEventStore,
)

def load_symatic_log():
    return SYMATIC_EVENTS.list()

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

def generate_symatic_equation(
    prev_phi,
    new_phi,
    reflection_text,
    *,
    event_store: SymaticEventStore | None = None,
    conversation_memory=None,
):
    """Generates a symbolic algebraic statement for a Φ-transition."""
    Δcoh = new_phi["Φ_coherence"] - prev_phi.get("Φ_coherence", 0)
    Δent = new_phi["Φ_entropy"] - prev_phi.get("Φ_entropy", 0)
    Δflux = new_phi["Φ_flux"] - prev_phi.get("Φ_flux", 0)

    op = phi_to_operator(Δcoh, Δent, Δflux)
    equation = f"Φ_state(t+1) = Φ_state(t) {op} ΔΦ({round(Δcoh,3)},{round(Δent,3)},{round(Δflux,3)})"

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operator": op,
        "equation": equation,
        "Δ": {"coherence": Δcoh, "entropy": Δent, "flux": Δflux},
        "reflection": reflection_text
    }

    # Append to log
    (event_store or SYMATIC_EVENTS).append(entry)

    # Record in AION memory
    (conversation_memory or MEMORY).record(f"SYMATICS: {equation}", new_phi, {
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
