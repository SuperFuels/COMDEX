# File: backend/modules/codex/bridges/resonant_insight_bridge.py
"""
CodexTrace Resonant Insight Bridge
──────────────────────────────────
Bridges the QQC↔AION resonance telemetry into CodexTrace's symbolic layer.
Each coherence sample from ResonantMemory is interpreted in symbolic form
(⊕ μ ⟲ ↔ πₛ) and logged for pattern-learning or semantic analytics.

Produces:
  • codex_resonant_insight.jsonl  — local insight log
  • codextrace_stream event (if CodexTrace bus is active)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from backend.QQC.core.resonant_memory import _memory

LOG_PATH = Path("backend/logs/codex/codex_resonant_insight.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
def _symbolic_map(ΔΦ: float, Δε: float, prediction: str) -> str:
    """Map resonance shifts to symbolic Symatics operators."""
    if prediction == "incoming_drift":
        return "⟲"   # resonance collapse / instability
    if prediction == "stabilizing":
        return "πₛ"  # phase-closure / coherence regain
    if abs(ΔΦ) < 0.01 and abs(Δε) < 0.05:
        return "↔"   # entanglement / stable coupling
    if ΔΦ > 0 and Δε < 0:
        return "⊕"   # constructive interference
    return "μ"       # measurement / decoherence


# ──────────────────────────────────────────────
def push_to_codextrace():
    """Compute ΔΦ, Δε trends from ResonantMemory and push to CodexTrace."""
    records = _memory.records[-5:]
    if len(records) < 2:
        print("[Codex::ResonantInsight] Insufficient resonance data for trend inference.")
        return None

    Φ_vals = [r["Φ_stability"] for r in records]
    ε_vals = [r["tolerance"] for r in records]

    ΔΦ = Φ_vals[-1] - Φ_vals[0]
    Δε = ε_vals[-1] - ε_vals[0]

    # Trend classification
    if ΔΦ < -0.02:
        prediction = "incoming_drift"
    elif ΔΦ > 0.05 and Δε < 0.2:
        prediction = "stabilizing"
    else:
        prediction = "steady"

    symbol = _symbolic_map(ΔΦ, Δε, prediction)

    insight = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ΔΦ": round(ΔΦ, 6),
        "Δε": round(Δε, 6),
        "prediction": prediction,
        "symbolic_operator": symbol,
        "avg_Φ": mean(Φ_vals),
        "avg_ε": mean(ε_vals),
    }

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(insight) + "\n")

    print(f"[Codex::ResonantInsight] ΔΦ={ΔΦ:+.4f}, Δε={Δε:+.4f} → {symbol} ({prediction})")

    # Optional — push to live Codex bus
    try:
        from backend.modules.codex.streams.codextrace_bus import post_event
        post_event("RESONANT_INSIGHT", insight)
    except Exception:
        pass

    return insight