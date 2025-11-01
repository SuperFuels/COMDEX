#!/usr/bin/env python3
"""
Tessaris Phase 14.1 - Resonant Heartbeat Generator (AION link)
Emits periodic coherence readings to data/aion_field/resonant_heartbeat.jsonl,
driving synchronization between AION resonance sensors and Tessaris harmonics.
"""

import json, time, math, random
from datetime import datetime, timezone
from pathlib import Path

HEARTBEAT_PATH = Path("data/aion_field/resonant_heartbeat.jsonl")
HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)

def emit_heartbeat():
    print("💓 Starting Tessaris Resonant Heartbeat Generator...")
    t0 = time.time()
    while True:
        t = time.time() - t0
        # Simulate harmonic coherence and small perturbation
        stability = 1.0 - abs(math.sin(t / 12)) * 0.02
        phi = math.sin(t / 8) * 0.001 + random.uniform(-0.0001, 0.0001)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stability": stability,
            "ΔΦ_coh": phi,
        }
        with open(HEARTBEAT_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"💓 Resonant heartbeat - stability={stability:.6f}, ΔΦ_coherence={phi:+.6f}")
        time.sleep(5.0)

if __name__ == "__main__":
    emit_heartbeat()