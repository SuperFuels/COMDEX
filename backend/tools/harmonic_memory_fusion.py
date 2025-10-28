#!/usr/bin/env python3
"""
🌌 Harmonic Memory Fusion — Phase 62 Tessaris Long-Term Integration
────────────────────────────────────────────────────────────────────────────
Combines reflection and governance histories into a single
temporal harmonic memory structure for persistent resonance learning.
"""

import json, time
from pathlib import Path
from statistics import fmean
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

Theta = ResonanceHeartbeat(namespace="global_theta")

REFLECTION_PATH = Path("data/analysis/reflection_log.json")
GOV_LOG_PATH = Path("data/analysis/governance_state.jsonl")
OUT = Path("data/analysis/harmonic_memory.json")

def _safe_read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def _safe_read_jsonl(path):
    entries = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries

def fuse_memories():
    reflection = _safe_read_json(REFLECTION_PATH)
    governance = _safe_read_jsonl(GOV_LOG_PATH)

    if not reflection or not governance:
        print("⚠️ Missing reflection or governance data.")
        return None

    avg_stability = reflection.get("avg_Δ_stability", 0)
    avg_drift = reflection.get("avg_Δ_drift", 0)
    avg_risk = fmean([g.get("avg_risk", 0) for g in governance])
    avg_gain = fmean([g.get("gain_mod", 1.0) for g in governance])

    harmony_memory = {
        "timestamp": time.time(),
        "avg_reflective_stability": round(avg_stability, 3),
        "avg_reflective_drift": round(avg_drift, 3),
        "avg_governance_risk": round(avg_risk, 3),
        "avg_gain_mod": round(avg_gain, 3),
        "harmony_integral": round(1 - (abs(avg_drift) + avg_risk) / 2, 3)
    }

    Theta.event(
        "harmonic_memory_update",
        stability=avg_stability,
        drift=avg_drift,
        risk=avg_risk,
        harmony=harmony_memory["harmony_integral"]
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(harmony_memory, indent=2))
    print(f"📘 Harmonic memory fused → {OUT}")
    return harmony_memory

def main():
    fused = fuse_memories()
    if fused:
        print(json.dumps(fused, indent=2))

if __name__ == "__main__":
    main()