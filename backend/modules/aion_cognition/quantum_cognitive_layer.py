#!/usr/bin/env python3
"""
Tessaris Phase 16 - Quantum Cognitive Layer (QCL)

Translates continuous resonance and control data into symbolic cognition
glyphs representing the Symatics Algebra primitives (⊕, ↔, ⟲, ∇, μ, π).
This marks the transition from numerical coherence control to symbolic
field cognition and reasoning.
"""

import json, time, math
from datetime import datetime, timezone
from pathlib import Path

# Paths
RQFS_PATH = Path("data/learning/rqfs_sync.jsonl")
RFC_PATH = Path("data/learning/rfc_weights.jsonl")
PHOTO_PATH = Path("data/qqc_field/photo_output/")
COG_PATH = Path("data/cognition/qcl_state.jsonl")
COG_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_latest_jsonl(path: Path):
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

def load_latest_photo():
    files = sorted(PHOTO_PATH.glob("*.photo"))
    if not files:
        return None
    latest = files[-1]
    try:
        with open(latest) as f:
            return json.load(f)
    except Exception:
        return None

def symbolic_projection(phi: float, drift: float, stability: float) -> str:
    """Map numeric coherence parameters to Symatic glyphs."""
    if abs(phi) < 1e-3 and stability > 0.99:
        return "⊕"  # superposition / harmony
    elif drift > 0.8:
        return "∇"  # collapse onset
    elif phi * drift < 0:
        return "↔"  # entanglement inversion
    elif abs(phi) > 0.005 and stability < 0.9:
        return "μ"  # measurement noise
    else:
        return "⟲"  # resonant steady state

def cognitive_cycle():
    """Perform one cognitive interpretation cycle."""
    rqfs = load_latest_jsonl(RQFS_PATH)
    rfc = load_latest_jsonl(RFC_PATH)
    photo = load_latest_photo()

    if not (rqfs and rfc and photo):
        print("⚠️ Waiting for resonance/coupler inputs (RQFS/RFC/Photo)...")
        return

    phi = rqfs.get("ΔΦ_obs", 0.0)
    drift = abs(rqfs.get("error", 0.0))
    stability = 1.0 - min(abs(rqfs.get("error", 0.0)), 1.0)
    nu_bias = rfc.get("nu_bias", 0.0)
    amp_gain = rfc.get("amp_gain", 1.0)

    glyph = symbolic_projection(phi, drift, stability)
    cog_state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "glyph": glyph,
        "Φ_harm": phi,
        "drift": drift,
        "stability": stability,
        "ν_bias": nu_bias,
        "amp_gain": amp_gain,
    }

    with open(COG_PATH, "a") as f:
        f.write(json.dumps(cog_state) + "\n")

    print(f"🧠 {glyph}  Φ={phi:+.5f} drift={drift:+.5f} stab={stability:+.3f}  "
          f"ν={nu_bias:+.3f} amp={amp_gain:+.3f}")

def run_qcl(interval: float = 5.0):
    print("🧠 Starting Tessaris Quantum Cognitive Layer (QCL)...")
    while True:
        cognitive_cycle()
        time.sleep(interval)

def main():
    run_qcl()

if __name__ == "__main__":
    main()