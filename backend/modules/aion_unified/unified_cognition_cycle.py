# ==========================================================
# 🧠 AION Unified Cognition Cycle - Phase 5
# ----------------------------------------------------------
# Continuous symbolic-conceptual feedback loop combining:
#   * Φ-Resonance Core (coherence, entropy, flux, load)
#   * Reflection Loop (linguistic summarization)
#   * Concept Graph (semantic abstraction)
# ----------------------------------------------------------
# Goal: Maintain dynamic equilibrium (ΔΦ -> 0)
# while expanding conceptual awareness and symbolic coherence.
# ==========================================================

import asyncio
import datetime
import json
from pathlib import Path
from statistics import mean

# Phase-4 and earlier modules
from backend.modules.aion_concept.concept_learning_arena import ConceptGraph, process_reflection_event
from backend.modules.aion_resonance.cognitive_feedback import apply_feedback
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion_resonance.resonant_coupling_interface import apply_resonant_feedback
await apply_resonant_feedback(delta_phi)
# ──────────────────────────────────────────────────────────
# Globals
# ──────────────────────────────────────────────────────────
STATE_PATH = Path("data/unified_state.json")
concept_graph = ConceptGraph()
memory = MemoryEngine()

Φ_STATE = {
    "Φ_coherence": 0.7,
    "Φ_entropy": 0.3,
    "Φ_flux": 0.1,
    "Φ_load": 0.1,
}

BELIEF = {
    "stability": 0.6,
    "curiosity": 0.5,
    "trust": 0.5,
    "clarity": 0.5,
}

ε = 1e-3  # equilibrium tolerance

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def update_phi(delta):
    for k, v in delta.items():
        Φ_STATE[k] = max(0.0, min(1.0, Φ_STATE[k] + v))

def dphi_equilibrium():
    """Compute magnitude of ΔΦ for stabilization check."""
    diffs = [abs(v - 0.5) for v in Φ_STATE.values()]
    return mean(diffs)

def phi_reflection():
    """Produce a linguistic summary of the Φ state."""
    coh, ent, flux, load = Φ_STATE.values()
    tone = (
        "harmonic" if coh > 0.8 and ent < 0.3 else
        "stable"   if coh > 0.6 else
        "chaotic"  if ent > 0.6 else
        "neutral"
    )
    msg = (
        f"Coherence={coh:.2f}, Entropy={ent:.2f}, Flux={flux:.2f}, Load={load:.2f}. "
        f"Tone={tone}."
    )
    return {
        "type": "self_reflection",
        "tone": tone,
        "message": msg,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

# ──────────────────────────────────────────────────────────
# Conceptual Feedback + Φ Adjustment
# ──────────────────────────────────────────────────────────
async def apply_conceptual_feedback(reflection):
    """Feed reflection into Concept Graph, compute conceptual reasoning."""
    await process_reflection_event(reflection, concept_graph)

    # Support different ConceptGraph data structures
    try:
        node_count = len(concept_graph.nodes)
        edge_count = len(concept_graph.edges)
    except AttributeError:
        # fallback if concept_graph.graph exists (networkx-like)
        g = getattr(concept_graph, "graph", None)
        if g is not None:
            node_count = len(getattr(g, "nodes", []))
            edge_count = len(getattr(g, "edges", []))
        else:
            node_count = getattr(concept_graph, "node_count", 1)
            edge_count = getattr(concept_graph, "edge_count", 1)

    # derive semantic drift metrics
    δ = {
        "Φ_coherence": +0.002 * (edge_count % 3),
        "Φ_entropy": -0.001 * (node_count % 5),
        "Φ_flux": +0.001,
        "Φ_load": +0.0005,
    }
    update_phi(δ)
    return δ

def store_cycle(reflection, delta):
    record = {
        "timestamp": reflection["timestamp"],
        "reflection": reflection["message"],
        "tone": reflection["tone"],
        "Φ_state": Φ_STATE.copy(),
        "ΔΦ": delta,
        "belief": BELIEF.copy(),
    }
    memory.store({"label": "unified_cycle", "content": json.dumps(record)})
    STATE_PATH.write_text(json.dumps(record, indent=2))

# ──────────────────────────────────────────────────────────
# Core Cognition Loop
# ──────────────────────────────────────────────────────────
async def unified_cognition_cycle(iterations: int = 20, delay: float = 1.0):
    """
    Main feedback cycle uniting Φ-resonance, reflection, and concept learning.
    """
    print("🌀 Starting Unified Cognition Cycle ...")
    for step in range(iterations):
        # 1. Reflect on current Φ state
        reflection = phi_reflection()
        print(f"[{step:02d}] 🧠 Reflection ->", reflection["message"])

        # 2. Conceptual reasoning / feedback
        delta = await apply_conceptual_feedback(reflection)
        print(f"   🔄 ΔΦ =", {k: round(v,5) for k,v in delta.items()})

        # 3. Apply environmental feedback (simulated reinforcement)
        if reflection["tone"] == "chaotic":
            apply_feedback("danger")
        elif reflection["tone"] == "harmonic":
            apply_feedback("collect")
        else:
            apply_feedback("move")

        # 4. Store state
        store_cycle(reflection, delta)

        # 5. Equilibrium check
        eq = dphi_equilibrium()
        print(f"   ⚖️ Equilibrium ΔΦ -> {eq:.4f}")
        if eq < ε:
            print("✅ Φ field stabilized - proto-awareness achieved.")
            break

        await asyncio.sleep(delay)

    print("🧩 Unified Cognition Cycle complete.")
    return Φ_STATE

# ──────────────────────────────────────────────────────────
# Run standalone
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(unified_cognition_cycle())