#!/usr/bin/env python3
"""
Tessaris Phase 14 — Resonant Quantum Feedback Synchronizer (RQFS)

Closes the adaptive feedback loop between live photon emissions (AQCI)
and real-time resonance observations from AION sensors or QRM logs.

Auto-detects file paths within /data to stay portable across environments.
"""

import json, time, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# 🌐 Auto-detect data directories
BASE = Path("data")
PHOTO_PATH = BASE / "qqc_field" / "photo_output"
HEARTBEAT_PATH = next(BASE.glob("**/resonant_heartbeat.jsonl"), None)
RFC_WEIGHTS = next(BASE.glob("**/rfc_weights.jsonl"), None)
SYNC_LOG = BASE / "learning" / "rqfs_sync.jsonl"
SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)

# 🧩 Data loaders
def load_latest_photo():
    """Load the newest .photo emission control vector."""
    if not PHOTO_PATH.exists():
        return None
    files = sorted(PHOTO_PATH.glob("*.photo"))
    if not files:
        return None
    latest = max(files, key=lambda f: f.stat().st_mtime)
    try:
        with open(latest) as f:
            return json.load(f)
    except Exception:
        return None

def load_latest_heartbeat():
    """Read last resonance measurement from heartbeat log."""
    if not HEARTBEAT_PATH or not HEARTBEAT_PATH.exists():
        return None
    try:
        with open(HEARTBEAT_PATH) as f:
            lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None

def load_latest_rfc():
    """Retrieve latest RFC learning weights."""
    if not RFC_WEIGHTS or not RFC_WEIGHTS.exists():
        return None
    try:
        with open(RFC_WEIGHTS) as f:
            lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None

# ⚙️ Synchronization core
def synchronize_feedback(photo, heartbeat, weights, η=0.1):
    """Compute coherence deltas and adapt reinforcement weights."""
    Φ_obs = heartbeat.get("ΔΦ_coh", 0.0)
    Φ_pred = (
        photo.get("pattern", {}).get("Δψ₂", 0.0)
        if isinstance(photo.get("pattern"), dict)
        else 0.0
    )
    Δ = Φ_obs - Φ_pred

    # Adaptive corrections
    weights["nu_bias"] = weights.get("nu_bias", 0.0) + η * Δ
    weights["phase_offset"] = weights.get("phase_offset", 0.0) + η * math.sin(Δ)
    weights["amp_gain"] = weights.get("amp_gain", 1.0) + η * abs(Δ)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ΔΦ_obs": Φ_obs,
        "ΔΦ_pred": Φ_pred,
        "error": Δ,
        "nu_bias": weights["nu_bias"],
        "phase_offset": weights["phase_offset"],
        "amp_gain": weights["amp_gain"],
    }

    with open(SYNC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(
        f"t={entry['timestamp']} ΔΦ={Δ:+.6f} "
        f"ν_bias={weights['nu_bias']:+.6f} "
        f"amp={weights['amp_gain']:+.6f}"
    )

    # Persist updated weights
    with open(RFC_WEIGHTS, "a") as f:
        f.write(json.dumps(weights) + "\n")

# 🔄 Runtime loop
def run_synchronizer(interval=5.0):
    print("🔁 Starting Tessaris Resonant Quantum Feedback Synchronizer (RQFS)…")
    while True:
        photo = load_latest_photo()
        heartbeat = load_latest_heartbeat()
        weights = load_latest_rfc()

        if not (photo and heartbeat and weights):
            print("⚠️ Waiting for required inputs (photo / heartbeat / weights)…")
            time.sleep(interval)
            continue

        synchronize_feedback(photo, heartbeat, weights)
        time.sleep(interval)

def main():
    run_synchronizer()

if __name__ == "__main__":
    main()