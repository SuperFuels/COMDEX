#!/usr/bin/env python3
"""
Tessaris Phase 23 - Symbolic Resonance Export Layer (SREL)

Translates consolidated meta-resonant telemetry into symbolic glyph streams
for Symatics Algebra integration (⊕, ⟲, ↔, ∇, μ, π).  Each line represents
a symbolic projection of the underlying resonance field.

Output:
    data/symatics/symbolic_resonance_stream.glyph
"""

import json, math, time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
DATA = Path("data")
META_FILE = DATA / "telemetry" / "meta_resonant_telemetry.jsonl"
OUT_PATH  = DATA / "symatics"
OUT_FILE  = OUT_PATH / "symbolic_resonance_stream.glyph"
OUT_PATH.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Symbolic quantization map
# ---------------------------------------------------------------------
def glyph_from_params(nu, phi, amp):
    """Map resonance parameters -> Symatics glyph."""
    # Frequency drift ν
    if abs(nu) < 0.5:
        base = "⊕"   # harmonic superposition
    elif abs(nu) < 1.0:
        base = "⟲"   # resonance
    else:
        base = "↔"   # entangled / divergent

    # Phase offset φ
    if phi > 0.2:
        mod = "μ"    # measurement / positive phase
    elif phi < -0.2:
        mod = "∇"    # collapse / negative phase
    else:
        mod = "π"    # neutral / projection

    # Amplitude A
    if amp > 6:
        energy = "💡"
    elif amp < 3:
        energy = "🌊"
    else:
        energy = "*"

    return f"{energy}{base}{mod}"

# ---------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------
def process_latest_entry(line):
    """Convert one consolidated JSONL line into symbolic form."""
    try:
        entry = json.loads(line)
        rfc = entry.get("rfc", {})
        rqfs = entry.get("rqfs", {})
        nu  = rqfs.get("nu_bias", rfc.get("nu_bias", 0.0))
        phi = rqfs.get("phase_offset", rfc.get("phase_offset", 0.0))
        amp = rqfs.get("amp_gain", rfc.get("amp_gain", 1.0))
        glyph = glyph_from_params(nu, phi, amp)

        symbol = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nu": nu,
            "phi": phi,
            "amp": amp,
            "glyph": glyph,
        }

        with open(OUT_FILE, "a") as f:
            f.write(json.dumps(symbol, ensure_ascii=False) + "\n")

        print(f"🪶  t={symbol['timestamp']} | ν={nu:+.3f} φ={phi:+.3f} A={amp:+.3f} -> glyph={glyph}")

    except Exception as e:
        print(f"⚠️  Parse error: {e}")

# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------
def run_exporter(interval=5.0):
    print("🪶  Starting Tessaris Symbolic Resonance Export Layer (SREL)...")
    if not META_FILE.exists():
        print("⚠️  Waiting for meta_resonant_telemetry.jsonl ...")
    last_size = 0
    while True:
        if META_FILE.exists():
            new_size = META_FILE.stat().st_size
            if new_size > last_size:
                with open(META_FILE) as f:
                    lines = f.readlines()
                if lines:
                    process_latest_entry(lines[-1])
                last_size = new_size
        time.sleep(interval)

def main():
    run_exporter()

if __name__ == "__main__":
    main()