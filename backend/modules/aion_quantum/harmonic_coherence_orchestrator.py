#!/usr/bin/env python3
"""
Tessaris Phase 15 — Harmonic Coherence Orchestrator (HCO)

Central orchestration layer synchronizing Tessaris adaptive subsystems:
RFC ↔ AQCI ↔ RQFS ↔ AION.

The HCO computes harmonic coherence metrics across all live data feeds,
monitors drift, and rebalances gain/phase bias dynamically.

Output: data/learning/hco_state.jsonl
"""

import json, time, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
RFC_PATH = Path("data/learning/rfc_weights.jsonl")
RQFS_PATH = Path("data/learning/rqfs_sync.jsonl")
HEARTBEAT_PATH = Path("data/aion_field/resonant_heartbeat.jsonl")
PHOTO_PATH = Path("data/qqc_field/photo_output/")

HCO_LOG = Path("data/learning/hco_state.jsonl")
HCO_LOG.parent.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------

def read_last_jsonl(path: Path):
    """Read last JSON line from a .jsonl file."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None

def read_latest_photo():
    """Get metadata from the most recent .photo file."""
    files = sorted(PHOTO_PATH.glob("*.photo"))
    if not files:
        return None
    try:
        with open(files[-1]) as f:
            return json.load(f)
    except Exception:
        return None

# -------------------------------------------------------------------
# Harmonic Computation
# -------------------------------------------------------------------

def compute_harmonic_state(rfc, rqfs, heartbeat, photo):
    """
    Compute unified harmonic metrics across active subsystems.
    """
    # Extract representative coherence measures
    Φ_rfc = rfc.get("phase_offset", 0.0)
    Φ_rqfs = rqfs.get("error", 0.0)
    Φ_beat = heartbeat.get("ΔΦ_coh", 0.0)
    Φ_photo = photo.get("pattern", {}).get("Δψ₂", 0.0)

    # Harmonic mean of coherence terms (avoid div-by-zero)
    values = np.array([Φ_rfc, Φ_rqfs, Φ_beat, Φ_photo], dtype=float)
    Φ_harm = len(values) / np.sum(1.0 / (values + 1e-9))

    # System drift: deviation between subsystems
    drift = float(np.std(values))

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "Φ_rfc": Φ_rfc,
        "Φ_rqfs": Φ_rqfs,
        "Φ_beat": Φ_beat,
        "Φ_photo": Φ_photo,
        "Φ_harm": Φ_harm,
        "drift": drift,
    }

def apply_rebalance(rfc, rqfs, drift, η=0.05):
    """
    Apply small global rebias when drift exceeds threshold.
    """
    if drift < 0.05:
        return rfc  # stable enough

    adjust = η * drift
    rfc["nu_bias"] = rfc.get("nu_bias", 0.0) - adjust
    rfc["phase_offset"] = rfc.get("phase_offset", 0.0) - adjust / 2
    rfc["amp_gain"] = rfc.get("amp_gain", 1.0) - adjust / 3
    return rfc

# -------------------------------------------------------------------
# Main Orchestrator Loop
# -------------------------------------------------------------------

def run_orchestrator(interval=5.0):
    print("🎛️  Starting Tessaris Harmonic Coherence Orchestrator (HCO)…")

    while True:
        # Load subsystem states
        rfc = read_last_jsonl(RFC_PATH)
        rqfs = read_last_jsonl(RQFS_PATH)
        heartbeat = read_last_jsonl(HEARTBEAT_PATH)
        photo = read_latest_photo()

        if not (rfc and rqfs and heartbeat and photo):
            print("⚠️ Waiting for subsystem telemetry (RFC/RQFS/Heartbeat/Photo)…")
            time.sleep(interval)
            continue

        # Compute harmonic state
        state = compute_harmonic_state(rfc, rqfs, heartbeat, photo)

        # Apply rebalance if needed
        new_rfc = apply_rebalance(rfc, rqfs, state["drift"])
        if new_rfc != rfc:
            with open(RFC_PATH, "a") as f:
                f.write(json.dumps(new_rfc) + "\n")
            print(f"♻️  Rebalanced RFC (Δ={state['drift']:+.4f}) → ν={new_rfc['nu_bias']:+.6f}")

        # Log harmonic coherence state
        with open(HCO_LOG, "a") as f:
            f.write(json.dumps(state) + "\n")

        print(
            f"t={state['timestamp']} "
            f"Φ_harm={state['Φ_harm']:+.6f} drift={state['drift']:+.6f}"
        )

        time.sleep(interval)

def main():
    run_orchestrator()

if __name__ == "__main__":
    main()