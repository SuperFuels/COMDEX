#!/usr/bin/env python3
"""
Tessaris PAL Resonance Stability Test
──────────────────────────────────────────────
Verifies convergence and equilibrium behavior
for the SQI-augmented PAL system.
"""

import json, time
from pathlib import Path
from backend.modules.aion_perception.pal_core import PAL, self_tune

# ─────────────────────────────────────────────
# Tunable SQI parameters
# ─────────────────────────────────────────────
SQI_TRIGGER_THRESHOLD = 0.045      # predictive trigger threshold
SQI_PREDICTIVE_MODE = True         # trigger before full collapse
EPSILON_LOCK_BAND = 0.010          # equilibrium tolerance
SAVE_INTERVAL = 200                # persistence window (rounds)

# ─────────────────────────────────────────────
# Initialize PAL instance
# ─────────────────────────────────────────────
pal = PAL(k=3, epsilon=0.08)
pal.load()
pal.verbose = True

print(f"\n🧠 Loaded {len(pal.memory)} exemplars - beginning resonance test")

prompts = ["align token", "stabilize field", "trace resonance", "harmonize pattern"]
options = ["Ω", "λ", "ψ", "Φ"]
correct_map = {
    "align token": "Ω",
    "stabilize field": "λ",
    "trace resonance": "ψ",
    "harmonize pattern": "Φ",
}

# ─────────────────────────────────────────────
# Run the tuning loop
# ─────────────────────────────────────────────
self_tune(
    pal,
    prompts,
    options,
    correct_map=correct_map,
    max_rounds=600,
    target_acc=0.96,
    momentum=0.35,
    learning_rate=0.12,
)

# ─────────────────────────────────────────────
# Stability report
# ─────────────────────────────────────────────
state_path = Path("data/prediction/pal_state.json")
if state_path.exists():
    state = json.load(open(state_path))
    print("\n📊 === PAL Resonance Summary ===")
    print(f"ε = {state['epsilon']:.3f}")
    print(f"k = {state['k']}")
    print(f"w = {state['memory_weight']:.3f}")
    print(f"Δε lock band = {EPSILON_LOCK_BAND}")
    print(f"SQI predictive mode = {SQI_PREDICTIVE_MODE}")
else:
    print("⚠️ No state file found, run may not have persisted.")