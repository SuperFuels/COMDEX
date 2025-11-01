"""
Tessaris Codex - Temporal Resonance Predictor
---------------------------------------------
Predicts near-term coherence drift by modelling ΔΦ / Δε trends
from CodexTrace Resonant Insight and AION-QQC telemetry.
"""

from __future__ import annotations
import os, json, math, time
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any

INSIGHT_LOG_PATH = "backend/logs/codex/codex_resonant_insight.jsonl"
FORECAST_LOG_PATH = "backend/logs/codex/predictor_forecast.jsonl"
WINDOW = 25  # recent events to consider


def load_recent_insights(limit: int = WINDOW) -> List[Dict[str, Any]]:
    """Return last <limit> symbolic resonance events."""
    if not os.path.exists(INSIGHT_LOG_PATH):
        return []
    with open(INSIGHT_LOG_PATH, "r") as f:
        lines = f.readlines()[-limit:]
    data = []
    for l in lines:
        try:
            data.append(json.loads(l))
        except json.JSONDecodeError:
            continue
    return data


def compute_trend(events: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute linear ΔΦ / Δε trends and forecast next phase."""
    if len(events) < 3:
        # not enough data yet
        return {"forecast_phi": None, "forecast_eps": None, "stability": 0.0}

    dphi = np.array([e.get("ΔΦ", 0.0) for e in events])
    deps = np.array([e.get("Δε", 0.0) for e in events])
    t = np.arange(len(events))

    slope_phi, _ = np.polyfit(t, dphi, 1)
    slope_eps, _ = np.polyfit(t, deps, 1)

    mean_phi = np.mean(dphi)
    mean_eps = np.mean(deps)

    forecast_phi = mean_phi + slope_phi
    forecast_eps = mean_eps + slope_eps

    var_phi = np.var(dphi)
    var_eps = np.var(deps)
    stability = 1.0 - min(1.0, math.sqrt(var_phi + var_eps))

    return {
        "forecast_phi": float(forecast_phi),
        "forecast_eps": float(forecast_eps),
        "stability": float(stability),
    }


def save_forecast(result: Dict[str, Any]):
    """Append forecast result to log."""
    os.makedirs(os.path.dirname(FORECAST_LOG_PATH), exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    with open(FORECAST_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def run_temporal_predictor():
    """Main entrypoint: load -> compute -> save -> print."""
    events = load_recent_insights(WINDOW)
    result = compute_trend(events)
    save_forecast(result)

    if result["forecast_phi"] is None:
        print("[Predictor] Waiting for sufficient μ-events to compute trend...")
        return

    print(
        f"[Predictor] ΔΦ̂={result['forecast_phi']:+.4f}, "
        f"Δε̂={result['forecast_eps']:+.4f}, "
        f"σ̂={result['stability']:.3f}"
    )


if __name__ == "__main__":
    while True:
        run_temporal_predictor()
        time.sleep(5.0)