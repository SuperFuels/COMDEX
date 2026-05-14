"""
Symatic Closure Verifier
────────────────────────
Validates symbolic ↔ telemetry coherence closure under πs constraints.

Reads:
  * Symbolic resonance events -> backend/logs/codex/codex_resonant_insight.jsonl
  * AION telemetry stream -> backend/logs/telemetry/Φ_stream.jsonl
  * Predictor forecast -> backend/logs/codex/predictor_forecast.jsonl

Computes:
  * ΔΦ(symbolic) vs ΔΦ(telemetry)
  * closure ratio πs = 1 - |ΔΦ_sym - ΔΦ_phys|
  * weighted confidence = πs * σ̂ (predictor confidence)

Logs:
  backend/logs/verifiers/symatic_closure.jsonl
"""

from __future__ import annotations
import os, json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

INSIGHT_PATH = Path("backend/logs/codex/codex_resonant_insight.jsonl")
TELEMETRY_PATH = Path("backend/logs/telemetry/Φ_stream.jsonl")
FORECAST_PATH = Path("backend/logs/codex/predictor_forecast.jsonl")
LOG_PATH = Path("backend/logs/verifiers/symatic_closure.jsonl")

def load_jsonl(path: Path, limit: int = 50):
    if not path.exists():
        return []
    with open(path, "r") as f:
        lines = f.readlines()[-limit:]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records

def compute_closure(insights, telemetry, forecast):
    """Compute πs closure ratio from symbolic vs physical Φ deltas."""
    if not insights or not telemetry:
        return None

    sym_deltas = [e.get("ΔΦ", 0.0) for e in insights[-10:]]
    phys_values = [t.get("Φ_stability_index", 0.0) for t in telemetry[-10:] if "Φ_stability_index" in t]

    if len(phys_values) < 2:
        return None

    ΔΦ_sym = mean(sym_deltas)
    ΔΦ_phys = phys_values[-1] - phys_values[0]
    σ̂ = forecast.get("stability", 1.0) if forecast else 1.0

    πs = max(0.0, min(1.0, 1.0 - abs(ΔΦ_sym - ΔΦ_phys)))
    confidence = πs * σ̂

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ΔΦ_sym": ΔΦ_sym,
        "ΔΦ_phys": ΔΦ_phys,
        "πs": πs,
        "σ̂": σ̂,
        "closure_confidence": confidence,
    }
    return record

def verify_symatic_closure():
    """Perform a single Symatic closure verification pass."""
    insights = load_jsonl(INSIGHT_PATH)
    telemetry = load_jsonl(TELEMETRY_PATH)
    forecast_list = load_jsonl(FORECAST_PATH)
    forecast = forecast_list[-1] if forecast_list else {}

    record = compute_closure(insights, telemetry, forecast)
    if not record:
        print("[Verifier] Waiting for sufficient data...")
        return

    os.makedirs(LOG_PATH.parent, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    status = "closed" if record["πs"] > 0.85 else "open"
    print(
        f"[Verifier] πs={record['πs']:.3f}, "
        f"ΔΦ_sym={record['ΔΦ_sym']:+.4f}, ΔΦ_phys={record['ΔΦ_phys']:+.4f}, "
        f"σ̂={record['σ̂']:.3f}, status={status}"
    )
    return record

if __name__ == "__main__":
    verify_symatic_closure()