#!/usr/bin/env python3
"""
Tessaris Phase 12 — Reinforcement Feedback Coupler (RFC)

Links AION’s replayed resonance fields with a self-learning feedback loop.
Computes error between predicted and observed Φ_coh, updates local parameters,
and logs harmonic adaptation weights.
"""

import json, time, os, math
from datetime import datetime
from pathlib import Path
import numpy as np

RFC_PATH = Path("data/learning/rfc_weights.jsonl")
RFC_PATH.parent.mkdir(parents=True, exist_ok=True)

def compute_error(phi_pred: float, phi_obs: float) -> float:
    """Simple phase-coherence error metric."""
    return phi_obs - phi_pred

def update_weights(state: dict, lr: float = 0.01) -> dict:
    """
    Perform one-step reinforcement update.
    Adjusts ν-bias, phase offset, and amplitude gain.
    """
    err = state["error"]
    state["nu_bias"]     += lr * err
    state["phase_offset"] += lr * math.sin(err)
    state["amp_gain"]    += lr * abs(err)
    state["step"]        += 1
    return state

def reinforcement_cycle(frames, lr=0.01):
    """Iterate through replayed frames and apply feedback learning."""
    print("🧠 Starting Tessaris Reinforcement Feedback Coupler (RFC)…")

    state = {
        "step": 0,
        "nu_bias": 0.0,
        "phase_offset": 0.0,
        "amp_gain": 1.0,
    }

    for i, frame in enumerate(frames):
        phi_obs = frame.get("Φ_coh") or frame.get("Phi") or 0.0
        phi_pred = np.tanh(state["amp_gain"] * (state["nu_bias"] + state["phase_offset"]))
        err = compute_error(phi_pred, phi_obs)

        state["error"] = err
        state = update_weights(state, lr)

        print(f"t={i:03d} Φ_obs={phi_obs:+.6f} Φ_pred={phi_pred:+.6f} Δ={err:+.6f} "
              f"| ν_bias={state['nu_bias']:+.4f} amp={state['amp_gain']:+.4f}")

        RFC_PATH.open("a").write(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "t": i,
            "phi_obs": phi_obs,
            "phi_pred": phi_pred,
            "error": err,
            "nu_bias": state["nu_bias"],
            "phase_offset": state["phase_offset"],
            "amp_gain": state["amp_gain"],
        }) + "\n")

        time.sleep(0.05)

    print(f"✅ RFC complete — {state['step']} learning cycles\n"
          f"Final ν_bias={state['nu_bias']:+.5f} amp_gain={state['amp_gain']:+.5f}")

def main():
    """Load latest QRM mesh replay and train feedback coupler."""
    qrm_dir = Path("data/qqc_field/mesh_exports")
    files = sorted(qrm_dir.glob("resonance_*.qrm.gz"))
    if not files:
        print("❌ No QRM mesh found.")
        return
    latest = files[-1]
    import gzip
    payload = json.loads(gzip.open(latest, "rt").read())

    # reconstruct frames using dict-of-lists pattern
    data = payload.get("data", {})
    keys = list(data.keys())
    n = len(data[keys[0]]) if keys else 0
    frames = [{k: data[k][i] for k in keys} for i in range(n)]

    reinforcement_cycle(frames)

if __name__ == "__main__":
    main()