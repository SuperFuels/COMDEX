"""
AION Feedback Loop Autotuner
────────────────────────────
Links Temporal Resonance Predictor outputs to AION-QQC control weights.

When σ̂ (stability score) drops or ΔΦ̂ shows drift,
the autotuner increases corrective gain and audit frequency.
When σ̂ rises, it relaxes parameters gradually.

Log: backend/logs/governance/autotuner_log.jsonl
"""

from __future__ import annotations
import os, json
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.codex.predictors.temporal_resonance_predictor import run_temporal_predictor
from backend.QQC.core.rlk_state import set_tolerance, set_audit_interval, get_state

FORECAST_PATH = Path("backend/logs/codex/predictor_forecast.jsonl")
LOG_PATH = Path("backend/logs/governance/autotuner_log.jsonl")

DEFAULT_GAIN = 1.0
DEFAULT_AUDIT = 10


def read_latest_forecast():
    """Read last forecast entry."""
    if not FORECAST_PATH.exists():
        return None
    with open(FORECAST_PATH, "r") as f:
        lines = f.readlines()
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def compute_adjustment(forecast):
    """Derive new gain/audit adjustments based on predicted drift."""
    ΔΦ = forecast.get("forecast_phi", 0.0)
    Δε = forecast.get("forecast_eps", 0.0)
    σ̂ = forecast.get("stability", 1.0)

    # heuristics
    gain_adj = 1.0 + abs(ΔΦ) * (1.2 - σ̂)
    audit_adj = 1.0 + abs(Δε) * (1.0 - σ̂)

    return gain_adj, audit_adj, σ̂


def autotune():
    """Main entrypoint - run predictor, read output, adjust QQC parameters."""
    run_temporal_predictor()  # ensure fresh forecast
    forecast = read_latest_forecast()
    if not forecast:
        print("[Autotuner] No forecast available yet.")
        return

    gain_adj, audit_adj, σ̂ = compute_adjustment(forecast)
    state = get_state()

    # base values
    current_tolerance = state.get("tolerance", DEFAULT_GAIN)
    current_audit = state.get("audit_interval", DEFAULT_AUDIT)

    # adaptive tuning
    new_tolerance = max(1e-4, min(2.0, current_tolerance * gain_adj))
    new_audit = max(3, min(25, int(current_audit / audit_adj)))

    # apply live updates
    set_tolerance(new_tolerance)
    set_audit_interval(new_audit)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "forecast_phi": forecast.get("forecast_phi"),
        "forecast_eps": forecast.get("forecast_eps"),
        "σ̂": σ̂,
        "gain_adj": gain_adj,
        "audit_adj": audit_adj,
        "tolerance": new_tolerance,
        "audit_interval": new_audit,
    }

    os.makedirs(LOG_PATH.parent, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(
        f"[Autotuner] σ̂={σ̂:.3f}, ε->{new_tolerance:.4f}, "
        f"N->{new_audit}, gain_adj={gain_adj:.3f}, audit_adj={audit_adj:.3f}"
    )

    return record


if __name__ == "__main__":
    autotune()