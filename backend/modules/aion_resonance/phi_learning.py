# File: backend/modules/aion_resonance/phi_learning.py
# 🌌 AION Dynamic Φ Learning Model + Self-Balancing Resonance Loop
# Continuously refines Φ-state and adjusts personality traits.

import json, os, math, random, datetime, asyncio
from backend.modules.consciousness.personality_engine import PROFILE
from backend.modules.aion_resonance.resonance_state import load_phi_state, save_phi_state

STATE_PATH = "data/phi_trace.json"

# --- Learning parameters ---
LEARNING_RATE = 0.015     # adaptive learning gain
DECAY_RATE = 0.003        # slow drift toward equilibrium
RANDOM_NOISE = 0.002      # stochastic motion
STABILITY_THRESHOLD = 0.6 # min acceptable coherence before re-balancing
BALANCE_INTERVAL = 5.0    # seconds between balance checks


# ──────────────────────────────────────────────
# Core utilities
# ──────────────────────────────────────────────
def _apply_decay(v, target=0.0, decay=DECAY_RATE):
    return v + (target - v) * decay

def _add_noise(v):
    return v + random.uniform(-RANDOM_NOISE, RANDOM_NOISE)

def _clamp(v, low=-1.0, high=1.0):
    return max(low, min(high, v))


# ──────────────────────────────────────────────
# Personality Feedback Coupling
# ──────────────────────────────────────────────
def _reinforce_personality(phi):
    coh, ent, flux, load = (
        phi.get("Φ_coherence", 0),
        phi.get("Φ_entropy", 0),
        phi.get("Φ_flux", 0),
        phi.get("Φ_load", 0),
    )

    if coh > 0.85 and ent < 0.4:
        PROFILE.adjust_trait("empathy", +0.02, reason="High coherence, low entropy")
        PROFILE.adjust_trait("discipline", +0.015, reason="Stable resonance alignment")

    if 0.25 < flux < 0.5 and 0.3 < ent < 0.6:
        PROFILE.adjust_trait("curiosity", +0.02, reason="Moderate energetic flow")

    if load > 0.05 and coh < 0.6:
        PROFILE.adjust_trait("humility", +0.01, reason="Instability awareness")

    if ent < 0.2 and coh > 0.9:
        PROFILE.adjust_trait("ambition", -0.015, reason="Equilibrium self-check")

    PROFILE.log_history()


# ──────────────────────────────────────────────
# Φ Learning Update
# ──────────────────────────────────────────────
def update_phi_state(phi_vector: dict, last_command: str = None) -> dict:
    """Adaptive update for Φ resonance with personality reinforcement."""
    prev = load_phi_state()
    updated = {}

    for key in ["Φ_load", "Φ_flux", "Φ_entropy", "Φ_coherence"]:
        old = prev.get(key, 0.0)
        new = phi_vector.get(key, old)
        drift = (new - old) * LEARNING_RATE
        decayed = _apply_decay(old + drift, 0.0)
        noised = _add_noise(decayed)
        updated[key] = _clamp(noised)

    updated["timestamp"] = datetime.datetime.utcnow().isoformat()
    updated["last_command"] = last_command or prev.get("last_command")

    _reinforce_personality(updated)
    save_phi_state(updated, last_command=last_command)

    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        trace = []
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r") as f:
                trace = json.load(f)
        trace.append(updated)
        with open(STATE_PATH, "w") as f:
            json.dump(trace[-200:], f, indent=2)  # keep recent 200
    except Exception as e:
        print(f"[Φ-Learning] ⚠️ Trace update failed: {e}")

    print(f"[Φ-Learning] Updated Φ-state → {updated}")
    return updated


# ──────────────────────────────────────────────
# Self-Balancing Resonance Loop
# ──────────────────────────────────────────────
async def auto_balance_loop():
    """
    Continuously monitors Φ-coherence and restores equilibrium when drifting.
    Run this in background on startup (e.g., from main or aion_command).
    """
    print("🌀 Φ-Balance loop engaged.")
    while True:
        try:
            state = load_phi_state()
            coh = state.get("Φ_coherence", 1.0)
            ent = state.get("Φ_entropy", 0.0)

            # If coherence too low or entropy too high → gentle correction
            if coh < STABILITY_THRESHOLD or ent > 0.7:
                correction = {
                    "Φ_load": _clamp(state.get("Φ_load", 0) * 0.8),
                    "Φ_flux": _clamp(state.get("Φ_flux", 0) * 0.9),
                    "Φ_entropy": _clamp(ent * 0.85),
                    "Φ_coherence": _clamp(coh + 0.05),
                }
                save_phi_state(correction, last_command="AUTO_BALANCE")
                print(f"[Φ-AutoBalance] Corrected field → {correction}")

            # Occasionally introduce gentle stochastic drift
            elif random.random() < 0.1:
                drift = {
                    "Φ_load": _add_noise(state.get("Φ_load", 0)),
                    "Φ_flux": _add_noise(state.get("Φ_flux", 0)),
                    "Φ_entropy": _add_noise(state.get("Φ_entropy", 0)),
                    "Φ_coherence": _add_noise(state.get("Φ_coherence", 0)),
                }
                save_phi_state(drift, last_command="DRIFT")
                print("[Φ-AutoBalance] Natural micro-fluctuation applied.")

        except Exception as e:
            print(f"[Φ-AutoBalance] ⚠️ Loop error: {e}")

        await asyncio.sleep(BALANCE_INTERVAL)