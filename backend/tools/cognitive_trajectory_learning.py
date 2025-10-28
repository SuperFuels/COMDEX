#!/usr/bin/env python3
"""
🧠 Cognitive Trajectory Learning — Phase 60 Tessaris Predictive Layer
────────────────────────────────────────────────────────────────────────
Analyzes past reflection logs to forecast future resonance drift and
plan pre-emptive corrections.
"""

import json, time
from pathlib import Path
from statistics import fmean
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.dna_chain import dna_writer

Theta = ResonanceHeartbeat(namespace="global_theta")

ROL_PATH = Path("data/analysis/reflection_log.json")
HISTORY_PATH = Path("data/analysis/reflection_history.jsonl")
OUT = Path("data/analysis/trajectory_predictions.json")

def _safe_load(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def analyze_reflection_history():
    """Aggregate Δstability and Δdrift across all logged reflections."""
    if not HISTORY_PATH.exists():
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.touch()
    records = []
    for line in HISTORY_PATH.read_text().splitlines():
        try:
            records.append(json.loads(line))
        except Exception:
            continue
    return records

def append_reflection_snapshot():
    """Append latest reflection snapshot into history chain."""
    if not ROL_PATH.exists():
        return
    snapshot = _safe_load(ROL_PATH)
    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(snapshot) + "\n")

def predict_future_drift(records):
    """Estimate drift probability per engine from historical deltas."""
    engine_scores = {}
    for rec in records:
        for ref in rec.get("reflections", []):
            name = ref.get("engine")
            ds = ref.get("Δ_stability", 0)
            dd = ref.get("Δ_drift", 0)
            if name not in engine_scores:
                engine_scores[name] = {"ΔS": [], "ΔΔΦ": []}
            engine_scores[name]["ΔS"].append(ds)
            engine_scores[name]["ΔΔΦ"].append(dd)

    predictions = []
    for name, vals in engine_scores.items():
        avg_ds = fmean(vals["ΔS"]) if vals["ΔS"] else 0
        avg_dd = fmean(vals["ΔΔΦ"]) if vals["ΔΔΦ"] else 0
        risk = max(0.0, min(1.0, 0.5 - avg_ds + abs(avg_dd)))
        predictions.append({
            "engine": name,
            "avg_Δstability": round(avg_ds, 3),
            "avg_Δdrift": round(avg_dd, 3),
            "predicted_risk": round(risk, 3)
        })
    return predictions

def schedule_preemptive_tuning(predictions, risk_threshold=0.6):
    """Queue micro-tuning or DNA proposals for high-risk engines."""
    actions = []
    for p in predictions:
        if p["predicted_risk"] >= risk_threshold:
            name = p["engine"]
            Theta.tick()
            dna_writer.propose_dna_mutation(
                reason=f"Pre-emptive stabilization (risk={p['predicted_risk']})",
                source="Phase60_TrajectoryLearning",
                code_context="# 🔮 predictive placeholder",
                new_logic="# Auto-tuned resonance gain parameters"
            )
            Theta.event("trajectory_predicted", engine=name, risk=p["predicted_risk"])
            actions.append({"engine": name, "risk": p["predicted_risk"], "action": "preemptive_tuning"})
            print(f"🔮 Predicted drift for {name} (risk={p['predicted_risk']:.2f}) → tuning scheduled")
    return actions

def main():
    append_reflection_snapshot()
    records = analyze_reflection_history()
    predictions = predict_future_drift(records)
    actions = schedule_preemptive_tuning(predictions)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "timestamp": time.time(),
        "predictions": predictions,
        "actions": actions
    }, indent=2))
    print(f"📊 Trajectory predictions written → {OUT}")

if __name__ == "__main__":
    main()