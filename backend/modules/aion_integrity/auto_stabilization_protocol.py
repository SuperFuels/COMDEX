#!/usr/bin/env python3
"""
Tessaris Phase 21 - Auto-Stabilization Protocol (ASP)

Responds to CLRA coherence alerts and dynamically re-biases
the AION ↔ QQC field parameters to restore harmonic balance.
"""

import json, time, math
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
CLRA_LOG   = Path("data/learning/clra_audit.jsonl")
RFC_PATH   = Path("data/learning/rfc_weights.jsonl")
ASP_LOG    = Path("data/learning/asp_actions.jsonl")
ASP_LOG.parent.mkdir(parents=True, exist_ok=True)

# ── Parameters ────────────────────────────────────────────────────────
GAIN_CORR_NU    = 0.05   # correction scaling for ν-bias
GAIN_CORR_PHASE = 0.03   # correction scaling for phase
GAIN_CORR_AMP   = 0.02   # correction scaling for amplitude
INTERVAL        = 5.0    # seconds between checks

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

def apply_correction(weights, coherence, status):
    """Apply corrective feedback proportional to instability."""
    severity = 1.0 - coherence
    sign = -1 if "Unstable" in status else -0.5 if "Marginal" in status else 0

    # damp ν drift and re-center phase
    weights["nu_bias"]      += sign * GAIN_CORR_NU    * severity
    weights["phase_offset"] += sign * GAIN_CORR_PHASE * severity
    weights["amp_gain"]     -= sign * GAIN_CORR_AMP   * severity

    return weights

def stabilization_loop():
    print("🩺 Starting Tessaris Auto-Stabilization Protocol (ASP)...")
    while True:
        audit = load_last(CLRA_LOG)
        weights = load_last(RFC_PATH)

        if not (audit and weights):
            print("⚠️ Waiting for CLRA and RFC telemetry ...")
            time.sleep(INTERVAL)
            continue

        coherence = audit.get("coherence", 1.0)
        status = audit.get("status", "")
        if "Stable" in status:
            time.sleep(INTERVAL)
            continue

        new_weights = apply_correction(weights, coherence, status)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "coherence": coherence,
            "nu_bias": new_weights["nu_bias"],
            "phase_offset": new_weights["phase_offset"],
            "amp_gain": new_weights["amp_gain"]
        }

        with open(ASP_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

        with open(RFC_PATH, "a") as f:
            f.write(json.dumps(new_weights) + "\n")

        print(f"t={entry['timestamp']} | {status}-> applied Δ ("
              f"ν={new_weights['nu_bias']:+.4f}, "
              f"φ={new_weights['phase_offset']:+.4f}, "
              f"A={new_weights['amp_gain']:+.4f})")

        time.sleep(INTERVAL)

def main():
    stabilization_loop()

if __name__ == "__main__":
    main()