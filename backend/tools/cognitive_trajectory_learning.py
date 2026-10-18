#!/usr/bin/env python3
"""
🧠 Cognitive Trajectory Learning - Phase 60 Tessaris Predictive Layer
────────────────────────────────────────────────────────────────────────
Analyzes past reflection logs to forecast future resonance drift and
plan pre-emptive corrections.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import math
import time
from statistics import fmean
from typing import Any

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


REFLECTION_ENTITY_ID = "reflection_summary"
HISTORY_ENTITY_ID = "reflection_history"
PREDICTIONS_ENTITY_ID = "trajectory_predictions"
PREDICTIONS_SCHEMA = "tessaris.trajectory-predictions.v1"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default

def predict_future_drift(records):
    """Estimate drift probability per engine from historical deltas."""
    engine_scores = {}
    for rec in records:
        for ref in rec.get("reflections", []):
            name = ref.get("engine")
            ds = _number(ref.get("delta_stability", ref.get("Δ_stability")))
            dd = _number(ref.get("delta_drift", ref.get("Δ_drift")))
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

def schedule_preemptive_tuning(
    predictions,
    risk_threshold=0.6,
    proposal_handler: Callable[[Mapping[str, Any]], None] | None = None,
):
    """Queue micro-tuning or DNA proposals for high-risk engines."""
    actions = []
    for p in predictions:
        if p["predicted_risk"] >= risk_threshold:
            name = p["engine"]
            action = {"engine": name, "risk": p["predicted_risk"], "action": "preemptive_tuning"}
            actions.append(action)
            if proposal_handler is not None:
                proposal_handler(dict(action))
    return actions

def run_trajectory_learning(
    *,
    vault_store: AionLearningVaultStore | None = None,
    workspace_id: str | None = None,
    reflection: Mapping[str, Any] | None = None,
    risk_threshold: float = 0.6,
    proposal_handler: Callable[[Mapping[str, Any]], None] | None = None,
    runtime_handoff: Callable[[Mapping[str, Any]], None] | None = None,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    store = vault_store or AionLearningVaultStore(workspace_id=workspace_id)
    if not store.enabled:
        raise RuntimeError("trajectory_learning_guardian_store_not_configured")
    current = reflection if isinstance(reflection, Mapping) else store.get_state(REFLECTION_ENTITY_ID, {})
    history_payload = store.get_state(HISTORY_ENTITY_ID, {"records": []})
    records = list(history_payload.get("records", [])) if isinstance(history_payload, Mapping) else []
    if isinstance(current, Mapping) and current:
        records.append(dict(current))
    records = [row for row in records[-1000:] if isinstance(row, Mapping)]
    store.put_state(HISTORY_ENTITY_ID, {"schema": "tessaris.reflection-history.v1", "records": records})
    predictions = predict_future_drift(records)
    actions = schedule_preemptive_tuning(
        predictions,
        risk_threshold=max(0.0, min(1.0, _number(risk_threshold, 0.6))),
        proposal_handler=proposal_handler,
    )
    result = {
        "schema": PREDICTIONS_SCHEMA,
        "timestamp": _number(now()),
        "predictions": predictions,
        "actions": actions,
    }
    store.put_state(PREDICTIONS_ENTITY_ID, result)
    if runtime_handoff is not None:
        runtime_handoff(dict(result))
    return result


def main() -> None:
    result = run_trajectory_learning()
    print(f"Trajectory predictions stored in Guardian ({len(result['predictions'])})")

if __name__ == "__main__":
    main()
