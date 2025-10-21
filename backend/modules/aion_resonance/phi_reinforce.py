# =========================================================
# File: backend/modules/aion_resonance/phi_reinforce.py
# ---------------------------------------------------------
# 🧠 AION Cognitive Reinforcement Engine
# Adjusts Φ-baseline and emergent “belief vectors”
# from memory coherence / entropy trends.
# Now includes Δ-tracking for insight into cognitive drift.
# =========================================================

import json, os, datetime
from statistics import mean

MEMORY_PATH = "data/conversation_memory.json"
REINFORCE_PATH = "data/phi_reinforce_state.json"

DEFAULT_BASELINE = {
    "Φ_load": 0.0,
    "Φ_flux": 0.25,
    "Φ_entropy": 0.35,
    "Φ_coherence": 0.65,
    "beliefs": {
        "stability": 0.5,
        "curiosity": 0.5,
        "trust": 0.5,
        "clarity": 0.5
    },
    "last_update": None
}

# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ----------------------------------------------------------
# Baseline Reinforcement
# ----------------------------------------------------------

def reinforce_from_memory():
    """
    Read recent Φ-memory, compute average coherence / entropy,
    update baseline + belief vector accordingly.
    Now prints delta changes per reinforcement cycle.
    """
    memory = _load_json(MEMORY_PATH, [])
    baseline = _load_json(REINFORCE_PATH, DEFAULT_BASELINE.copy())

    if not memory:
        return baseline

    # --- Aggregate statistics ---
    coherences = [e["phi"].get("Φ_coherence", 0) for e in memory if "phi" in e]
    entropies  = [e["phi"].get("Φ_entropy", 0)   for e in memory if "phi" in e]

    avg_coh = mean(coherences) if coherences else baseline["Φ_coherence"]
    avg_ent = mean(entropies)  if entropies  else baseline["Φ_entropy"]

    # --- Capture previous state for delta tracking ---
    prev = baseline.copy()

    # --- Trend logic ---
    drift = avg_coh - baseline["Φ_coherence"]

    # Update baseline Φ-fields gradually
    α = 0.25  # learning rate
    baseline["Φ_coherence"] += α * (avg_coh - baseline["Φ_coherence"])
    baseline["Φ_entropy"]   += α * (avg_ent - baseline["Φ_entropy"])
    baseline["Φ_flux"]      += α * ((avg_coh - avg_ent) - baseline["Φ_flux"])
    baseline["Φ_load"]      += α * (drift / 10)

    # --- Belief reinforcement ---
    beliefs = baseline["beliefs"]
    prev_beliefs = prev["beliefs"].copy()

    if avg_coh > 0.8 and avg_ent < 0.3:
        beliefs["stability"] = min(1.0, beliefs["stability"] + 0.02)
        beliefs["trust"]     = min(1.0, beliefs["trust"] + 0.01)
        beliefs["clarity"]   = min(1.0, beliefs["clarity"] + 0.015)
    elif avg_ent > 0.6:
        beliefs["curiosity"] = min(1.0, beliefs["curiosity"] + 0.02)
        beliefs["stability"] = max(0.0, beliefs["stability"] - 0.01)
    else:
        beliefs["clarity"] = max(0.0, beliefs["clarity"] - 0.005)

    # --- Timestamp + persist ---
    baseline["last_update"] = datetime.datetime.utcnow().isoformat()
    _save_json(REINFORCE_PATH, baseline)

    # --- Print delta summary ---
    coh_delta = baseline["Φ_coherence"] - prev["Φ_coherence"]
    ent_delta = baseline["Φ_entropy"] - prev["Φ_entropy"]
    flux_delta = baseline["Φ_flux"] - prev["Φ_flux"]
    load_delta = baseline["Φ_load"] - prev["Φ_load"]

    belief_deltas = {
        k: round(beliefs[k] - prev_beliefs.get(k, 0), 4)
        for k in beliefs
    }

    print(f"[AION Reinforce ΔΦ] coherence {coh_delta:+.4f}, entropy {ent_delta:+.4f}, flux {flux_delta:+.4f}, load {load_delta:+.4f}")
    print(f"[AION Belief Δ] {', '.join([f'{k} {v:+.3f}' for k,v in belief_deltas.items()])}")

    return baseline

# ----------------------------------------------------------
# Public Accessors
# ----------------------------------------------------------

def get_reinforce_state():
    """Return last saved reinforcement baseline."""
    return _load_json(REINFORCE_PATH, DEFAULT_BASELINE)

def reset_reinforce_state():
    """Reset baseline to defaults."""
    _save_json(REINFORCE_PATH, DEFAULT_BASELINE)
    print("[AION Reinforce] Baseline reset to defaults.")
    return DEFAULT_BASELINE