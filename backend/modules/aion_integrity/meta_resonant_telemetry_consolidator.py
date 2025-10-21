#!/usr/bin/env python3
"""
Tessaris Phase 22 — Meta-Resonant Telemetry Consolidator (MRTC)

Aggregates and time-aligns live resonance telemetry across all active subsystems:
  • RFC  – Reinforcement Feedback Coupler
  • RQFS – Resonant Quantum Feedback Synchronizer
  • CLRA – Cross-Layer Resonance Auditor
  • ASP  – Auto-Stabilization Protocol
  • AQCI – Adaptive Quantum Control Interface
  • SFAE – Symbolic Forecast Engine
  • HCO  – Harmonic Coherence Orchestrator

Produces unified resonance telemetry → data/telemetry/meta_resonant_telemetry.jsonl
"""

import json, time
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
DATA = Path("data")
RFC_LOG = DATA / "learning" / "rfc_weights.jsonl"
RQFS_LOG = DATA / "learning" / "rqfs_sync.jsonl"
CLRA_LOG = DATA / "integrity" / "clra_audit.jsonl"
ASP_LOG  = DATA / "integrity" / "auto_stabilization.jsonl"
PHOTO_DIR = DATA / "qqc_field" / "photo_output"
OUT_LOG = DATA / "telemetry" / "meta_resonant_telemetry.jsonl"
OUT_LOG.parent.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def tail_jsonl(path: Path):
    """Return last valid JSON object from a .jsonl file, or None."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None

def latest_photo_meta():
    """Extract timestamp + pattern info from the newest .photo file."""
    files = sorted(PHOTO_DIR.glob("*.photo"))
    if not files:
        return None
    with open(files[-1]) as f:
        data = json.load(f)
    return {
        "photo_file": files[-1].name,
        "pattern": data.get("pattern", {}),
        "timestamp": data.get("timestamp", "")
    }

# --------------------------------------------------------------------------- #
# Core consolidator
# --------------------------------------------------------------------------- #
def consolidate_once():
    rfc  = tail_jsonl(RFC_LOG)
    rqfs = tail_jsonl(RQFS_LOG)
    clra = tail_jsonl(CLRA_LOG)
    asp  = tail_jsonl(ASP_LOG)
    photo = latest_photo_meta()

    if not any([rfc, rqfs, clra, asp, photo]):
        print("⚠️  No telemetry available yet…")
        return

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rfc": rfc,
        "rqfs": rqfs,
        "clra": clra,
        "asp": asp,
        "photo": photo,
    }

    with open(OUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    ν = (rqfs or {}).get("nu_bias", 0.0)
    ϕ = (rfc or {}).get("phase_offset", 0.0)
    A = (asp or {}).get("amp_gain", (rfc or {}).get("amp_gain", 1.0))
    print(f"📡  Consolidated | ν={ν:+.4f} ϕ={ϕ:+.4f} A={A:+.4f}")

# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #
def main(interval=5.0):
    print("📡 Starting Tessaris Meta-Resonant Telemetry Consolidator (MRTC)…")
    while True:
        consolidate_once()
        time.sleep(interval)

if __name__ == "__main__":
    main()