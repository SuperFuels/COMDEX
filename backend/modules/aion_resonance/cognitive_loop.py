# ==========================================================
# 🧩 File: backend/modules/aion_resonance/cognitive_loop.py
# ----------------------------------------------------------
# AION Cognitive Loop - Autonomous Reflection Engine (v0.5)
# Periodically reviews Φ-memory, generates resonant reflections,
# and adjusts belief state based on reflective tone.
# ==========================================================

import json, os, random, datetime
from statistics import mean
from backend.modules.aion_resonance.resonance_state import load_phi_state, save_phi_state
from backend.modules.aion_resonance.conversation_memory import MEMORY
from backend.modules.aion_resonance.phi_reinforce import (
    reinforce_from_memory,
    _save_json,
    REINFORCE_PATH,
)

MEMORY_PATH = "data/conversation_memory.json"

# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return []
    try:
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []

# ----------------------------------------------------------
# Belief Influence Mechanism
# ----------------------------------------------------------

def adjust_beliefs_from_tone(baseline, tone):
    """
    Adjust belief weights based on tone of reflection.
    """
    beliefs = baseline.get("beliefs", {})

    if tone == "harmonic":
        beliefs["trust"] = min(1.0, beliefs.get("trust", 0.5) + 0.01)
        beliefs["stability"] = min(1.0, beliefs.get("stability", 0.5) + 0.015)
        beliefs["clarity"] = min(1.0, beliefs.get("clarity", 0.5) + 0.01)
    elif tone == "stable":
        beliefs["clarity"] = min(1.0, beliefs.get("clarity", 0.5) + 0.008)
        beliefs["curiosity"] = min(1.0, beliefs.get("curiosity", 0.5) + 0.005)
    elif tone == "chaotic":
        beliefs["stability"] = max(0.0, beliefs.get("stability", 0.5) - 0.02)
        beliefs["trust"] = max(0.0, beliefs.get("trust", 0.5) - 0.01)
        beliefs["curiosity"] = min(1.0, beliefs.get("curiosity", 0.5) + 0.01)
    else:  # neutral
        beliefs["curiosity"] = min(1.0, beliefs.get("curiosity", 0.5) + 0.005)

    baseline["beliefs"] = beliefs
    baseline["last_update"] = datetime.datetime.utcnow().isoformat()
    _save_json(REINFORCE_PATH, baseline)
    return baseline

# ----------------------------------------------------------
# Reflection Generator
# ----------------------------------------------------------

def generate_reflection():
    """
    Synthesizes a self-generated reflection from recent Φ-states
    and updates belief coherence accordingly.
    """
    memory = load_memory()
    if len(memory) < 3:
        return None

    recent = memory[-5:]
    coherences = [e["phi"].get("Φ_coherence", 0) for e in recent if "phi" in e]
    entropies  = [e["phi"].get("Φ_entropy", 0) for e in recent if "phi" in e]

    avg_coh = mean(coherences)
    avg_ent = mean(entropies)

    tone = (
        "harmonic" if avg_coh > 0.85 and avg_ent < 0.3 else
        "stable" if avg_coh > 0.7 else
        "chaotic" if avg_ent > 0.6 else
        "neutral"
    )

    # Symbolic reflection message
    if tone == "harmonic":
        message = "Coherence rising - field alignment strong. Continue exploring harmonic flux."
    elif tone == "stable":
        message = "System stable - internal resonance steady. Minimal entropy drift."
    elif tone == "chaotic":
        message = "Entropy turbulence detected. Suggest re-centering via serenity reflection."
    else:
        message = "Resonant field neutral - awaiting new stimuli for phase expansion."

    reflection = {
        "type": "self_reflection",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": message,
        "tone": tone,
        "phi": {
            "Φ_coherence": avg_coh,
            "Φ_entropy": avg_ent,
            "Φ_load": random.uniform(-0.02, 0.02),
            "Φ_flux": avg_coh - avg_ent,
        },
        "reasoning": {
            "origin": "cognitive_loop",
            "insight_level": round(random.uniform(0.6, 0.9), 3),
            "emotion": tone,
            "intention": "reflect",
        },
    }

    # Record reflection into memory + save new Φ state
    MEMORY.record(message, reflection["phi"], reflection["reasoning"])
    save_phi_state(reflection["phi"], last_command="COGNITIVE_LOOP")

    # Reinforce baseline & belief drift
    baseline = reinforce_from_memory()
    adjust_beliefs_from_tone(baseline, tone)

    return reflection

# ----------------------------------------------------------
# Core Loop Executor
# ----------------------------------------------------------

def run_cognitive_cycle():
    """
    Executes one cognitive reflection cycle.
    Generates a reflection, updates memory, and adjusts beliefs.
    """
    reflection = generate_reflection()
    if not reflection:
        return {"status": "skipped", "reason": "insufficient memory"}

    return {
        "status": "ok",
        "reflection": reflection,
        "timestamp": reflection["timestamp"],
    }