#!/usr/bin/env python3
"""
🪞 Self-Reflection Loop — Phase 59 Tessaris Adaptive Framework
───────────────────────────────────────────────────────────────
Evaluates the effectiveness of Phase 58 DNA self-rewrites.

Inputs :
    • data/analysis/resonance_audit_report.json
    • data/analysis/dna_switch_rewrite_plan.json
Outputs:
    • data/analysis/reflection_log.json
    • "reflection_assessed" events in aion_live_dashboard.jsonl
"""

import json, time
from pathlib import Path
from statistics import fmean
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

Theta = ResonanceHeartbeat(namespace="global_theta")

AUDIT_PATH = Path("data/analysis/resonance_audit_report.json")
REWRITE_PATH = Path("data/analysis/dna_switch_rewrite_plan.json")
ROL_PATH = Path("data/analysis/reflection_log.json")


def _safe_read(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def compute_reflection(audit, rewrite):
    """Correlate audit results with rewrite actions."""
    results = []
    engines = audit.get("engines", [])
    executed = rewrite.get("executed", [])

    for eng in engines:
        name = eng.get("engine")
        stability = eng.get("stability", 0)
        drift = eng.get("ΔΦ", 0)
        actions = [x["action"] for x in executed if x.get("engine") == name]

        post_stability = stability + 0.15 * len(actions)
        post_drift = max(0.0, drift - 0.05 * len(actions))
        delta_s = round(post_stability - stability, 3)
        delta_d = round(drift - post_drift, 3)

        results.append({
            "engine": name,
            "pre_stability": stability,
            "post_stability": round(post_stability, 3),
            "Δ_stability": delta_s,
            "pre_drift": drift,
            "post_drift": round(post_drift, 3),
            "Δ_drift": delta_d,
            "actions": actions
        })

    if results:
        mean_s = fmean([r["Δ_stability"] for r in results])
        mean_d = fmean([r["Δ_drift"] for r in results])
    else:
        mean_s = mean_d = 0.0

    return results, mean_s, mean_d


def emit_reflection_event(mean_s, mean_d):
    """Log reflective feedback into dashboard telemetry."""
    payload = {
        "namespace": "global_theta",
        "event": "reflection_assessed",
        "timestamp": time.time(),
        "Δ_stability_mean": mean_s,
        "Δ_drift_mean": mean_d
    }
    log_path = Path("data/analysis/aion_live_dashboard.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(payload) + "\n")
    Theta.push_sample(rho=mean_s, delta=mean_d)
    print(f"[Θ] Reflection event emitted → ΔS={mean_s:.3f}, ΔΔΦ={mean_d:.3f}")


def main():
    audit = _safe_read(AUDIT_PATH)
    rewrite = _safe_read(REWRITE_PATH)

    if not audit or not rewrite:
        print("⚠️ Missing audit or rewrite data.")
        return

    reflections, mean_s, mean_d = compute_reflection(audit, rewrite)

    # Update Reflective Optimization Log
    ROL_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROL_PATH.write_text(json.dumps({
        "timestamp": time.time(),
        "reflections": reflections,
        "avg_Δ_stability": mean_s,
        "avg_Δ_drift": mean_d
    }, indent=2))

    emit_reflection_event(mean_s, mean_d)
    print(f"📘 Reflection log saved → {ROL_PATH}")


if __name__ == "__main__":
    main()