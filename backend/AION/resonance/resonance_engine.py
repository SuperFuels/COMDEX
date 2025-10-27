"""
AION Resonance Engine — Phase 9
────────────────────────────────────────────
Handles SQI / ρ / Ī resonance updates and coherence realignment
for ingested Wiki Capsules, including symbolic energy E.
"""

import json, time
from pathlib import Path

RESONANCE_PATH = Path("data/aion/resonance_state.json")
RESONANCE_PATH.parent.mkdir(parents=True, exist_ok=True)

# ───────────────────────────────
# I/O Helpers
# ───────────────────────────────
def _load_state() -> dict:
    return json.load(open(RESONANCE_PATH, "r")) if RESONANCE_PATH.exists() else {}

def _save_state(state: dict):
    json.dump(state, open(RESONANCE_PATH, "w"), indent=2)


# ───────────────────────────────
# Core Resonance Logic
# ───────────────────────────────
def update_resonance(title: str, keywords=None):
    """Update AION resonance map for a given capsule."""
    state = _load_state()
    keywords = keywords or []
    now = time.time()

    # Compute symbolic resonance coefficients
    sqi = round(min(1.0, 0.5 + len(keywords) / 50.0), 3)
    coherence = round(0.6 + sqi / 2, 3)
    phase = round((hash(title) % 100) / 100, 3)
    resonance_energy = round((sqi * coherence) ** 0.5, 5)

    # Persist resonance state
    state[title] = {
        "timestamp": now,
        "SQI": sqi,
        "ρ": coherence,
        "Ī": phase,
        "E": resonance_energy,  # symbolic resonance energy
        "keywords": keywords,
    }

    _save_state(state)
    print(f"[AION-Resonance] {title}: SQI={sqi} ρ={coherence} Ī={phase} E={resonance_energy}")
    return state[title]


# ───────────────────────────────
# Query API
# ───────────────────────────────
def get_resonance(title: str):
    """Return current resonance state for a given title."""
    return _load_state().get(title)