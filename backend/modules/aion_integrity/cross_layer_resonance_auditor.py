#!/usr/bin/env python3
"""
Tessaris Phase 20 — Cross-Layer Resonance Auditor (CLRA)

Monitors consistency between AION / QQC subsystems:
  • Resonant Feedback (RQFS)
  • Symbolic Memory (ASM)
  • Forecast Engine (SFAE)
  • Harmonic Coherence (HCO)

Computes coherence metrics and raises alerts when divergence exceeds tolerance.
"""

import json, time, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# ── Data Inputs ────────────────────────────────────────────────
RQFS_PATH      = Path("data/learning/rqfs_sync.jsonl")
ASM_PATH       = Path("data/cognition/asm_memory.jsonl")
FORECAST_PATH  = Path("data/cognition/forecast_stream.jsonl")
HCO_PATH       = Path("data/learning/harmonic_field.log")
AUDIT_LOG      = Path("data/learning/clra_audit.jsonl")
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

# ── Parameters ─────────────────────────────────────────────────
TOLERANCE_DRIFT   = 0.25     # allowable ν drift delta
TOLERANCE_ENTROPY = 0.20     # allowable symbolic entropy variance
TOLERANCE_CONF    = 0.15     # allowable forecast confidence drop
INTERVAL          = 5.0      # seconds between audits

def load_last(path):
    if not path.exists():
        return None
    with open(path) as f:
        lines = f.readlines()
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except Exception:
        return None

def compute_coherence(rqfs, asm, forecast):
    if not (rqfs and asm and forecast):
        return None
    drift  = abs(rqfs.get("error", 0.0))
    entropy = asm.get("entropy", 0.0)
    conf    = forecast.get("confidence", 1.0)

    # simple scalar coherence score ∈ [0,1]
    coherence = math.exp(-(
        (drift / TOLERANCE_DRIFT)**2 +
        (entropy / TOLERANCE_ENTROPY)**2 +
        ((1-conf) / TOLERANCE_CONF)**2
    )/3)

    return coherence, drift, entropy, conf

def audit_loop():
    print("🧭 Starting Tessaris Cross-Layer Resonance Auditor (CLRA)…")
    while True:
        rqfs     = load_last(RQFS_PATH)
        asm      = load_last(ASM_PATH)
        forecast = load_last(FORECAST_PATH)

        result = compute_coherence(rqfs, asm, forecast)
        if not result:
            print("⚠️ Waiting for input telemetry (RQFS / ASM / SFAE)…")
            time.sleep(INTERVAL)
            continue

        coherence, drift, entropy, conf = result
        status = "✅ Stable" if coherence > 0.8 else "⚠️ Marginal" if coherence > 0.5 else "🚨 Unstable"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "coherence": round(coherence, 4),
            "drift": drift,
            "entropy": entropy,
            "confidence": conf,
            "status": status
        }

        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"t={entry['timestamp']} | C={entry['coherence']:.3f} | "
              f"ΔΦ={drift:+.3f} | H={entropy:.3f} | conf={conf:.3f} | {status}")

        time.sleep(INTERVAL)

def main():
    audit_loop()

if __name__ == "__main__":
    main()