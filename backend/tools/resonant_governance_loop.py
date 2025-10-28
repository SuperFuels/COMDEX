#!/usr/bin/env python3
"""
⚖️  Resonant Governance Loop — Phase 61 Tessaris Self-Regulation Layer
────────────────────────────────────────────────────────────────────────
Transforms predictive risk metrics into adaptive policy updates.

Inputs :
    • data/analysis/trajectory_predictions.json
Outputs:
    • data/analysis/governance_state.jsonl
    • "governance_update" telemetry events
"""

import json, time
from pathlib import Path
from statistics import fmean
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.consciousness.ethics_engine import evaluate_ethics_score

Theta = ResonanceHeartbeat(namespace="global_theta")
PRED_PATH = Path("data/analysis/trajectory_predictions.json")
LOG_PATH = Path("data/analysis/governance_state.jsonl")

def load_predictions():
    try:
        return json.loads(PRED_PATH.read_text()).get("predictions", [])
    except Exception:
        return []

def derive_policy(predictions):
    """Compute new governance thresholds."""
    if not predictions:
        return {"rewrite_rate": 0.0, "ethics_confidence": 0.7, "gain_mod": 1.0}

    risks = [p["predicted_risk"] for p in predictions]
    avg_risk = fmean(risks)
    max_risk = max(risks)

    # Dynamic thresholds
    rewrite_rate = min(1.0, avg_risk * 1.2)
    ethics_confidence = max(0.3, 1.0 - avg_risk)
    gain_mod = max(0.5, 1.2 - (max_risk * 0.5))

    return {
        "timestamp": time.time(),
        "avg_risk": round(avg_risk, 3),
        "max_risk": round(max_risk, 3),
        "rewrite_rate": round(rewrite_rate, 3),
        "ethics_confidence": round(ethics_confidence, 3),
        "gain_mod": round(gain_mod, 3),
    }

def apply_policy(policy):
    """Apply new modulation weights to Θ and ethics layer."""
    Theta.push_sample(rho=policy["gain_mod"], entropy=1 - policy["ethics_confidence"])
    ethics_test = evaluate_ethics_score("auto governance modulation")
    Theta.event("governance_update",
                avg_risk=policy["avg_risk"],
                gain_mod=policy["gain_mod"],
                ethics_score=ethics_test)
    print(f"[Θ] Governance updated → risk={policy['avg_risk']:.2f}, gain={policy['gain_mod']:.2f}")

def log_policy(policy):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(policy) + "\n")

def main():
    preds = load_predictions()
    policy = derive_policy(preds)
    apply_policy(policy)
    log_policy(policy)
    print(f"📘 Governance policy applied → {LOG_PATH}")

if __name__ == "__main__":
    main()