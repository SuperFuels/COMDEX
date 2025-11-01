#!/usr/bin/env python3
"""
Tessaris Phase 13 - Adaptive Quantum Control Interface (AQCI)

Bridges the Reinforcement Feedback Coupler (RFC) with the Quantum Quad Core (QQC)
Photon Interface. Applies learned ν-bias, phase, and amplitude adjustments to live
photon emission parameters.
"""

import os, json, time, math
from datetime import datetime
from pathlib import Path
import numpy as np

RFC_PATH = Path("data/learning/rfc_weights.jsonl")
PHOTO_OUT = Path("data/qqc_field/photo_output/")
PHOTO_OUT.mkdir(parents=True, exist_ok=True)

def load_latest_weights():
    """Load the most recent RFC weight entry."""
    if not RFC_PATH.exists():
        print("❌ No RFC weights found.")
        return None
    with open(RFC_PATH, "r") as f:
        lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])

def synthesize_photon_pattern(weights, base_freq=440.0):
    """Generate a photon emission control pattern from adaptive weights."""
    ν_bias = weights["nu_bias"]
    phase = weights["phase_offset"]
    amp = weights["amp_gain"]

    # Derive photon frequency triplet and modulation pattern
    ν1 = base_freq * amp
    ν2 = base_freq * (1 + ν_bias)
    ν3 = base_freq * (1 + math.sin(phase) * 0.05)

    Δψ1 = math.sin(phase)
    Δψ2 = amp * (1 + ν_bias)
    Δψ3 = math.cos(phase)

    pattern = {
        "Δψ1": Δψ1,
        "Δψ2": Δψ2,
        "Δψ3": Δψ3,
        "ν1": ν1,
        "ν2": ν2,
        "ν3": ν3,
        "stability": 1.0,
        "phase_shift": phase,
    }
    return pattern

def emit_to_photon_interface(pattern):
    """Emit control vector to QQC Photon Interface."""
    ts = datetime.utcnow().isoformat()
    out_path = PHOTO_OUT / f"adaptive_{ts}.photo"
    with open(out_path, "w") as f:
        json.dump({
            "timestamp": ts,
            "pattern": pattern,
            "source": "AION_AQCI"
        }, f, indent=2)
    print(f"💡 Emitted adaptive photon control -> {out_path.name}")

def adaptive_loop(interval=5.0):
    """Continuous adaptive emission loop."""
    print("🔄 Starting Tessaris Adaptive Quantum Control Interface (AQCI)...")
    while True:
        weights = load_latest_weights()
        if weights is None:
            print("⚠️ Waiting for RFC weights ...")
            time.sleep(interval)
            continue

        pattern = synthesize_photon_pattern(weights)
        emit_to_photon_interface(pattern)

        print(f"  ν_bias={weights['nu_bias']:+.6f}  "
              f"phase={weights['phase_offset']:+.6f}  "
              f"amp={weights['amp_gain']:+.6f}")
        time.sleep(interval)

def main():
    adaptive_loop()

if __name__ == "__main__":
    main()