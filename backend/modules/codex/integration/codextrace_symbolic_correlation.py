"""
CodexTrace Symbolic↔Telemetry Correlation Bridge
────────────────────────────────────────────────
Links hardware resonance telemetry (ψ κ T Φ metrics)
with symbolic operator events (⊕ μ ⟲ ↔ πs) recorded
by the Resonant Insight Bridge and AION telemetry.

Purpose:
  * Correlate physical resonance (ΔΦ, Δε, κ) with symbolic logic events.
  * Generate symbolic-physical coherence reports to CodexTrace.
  * Build a cumulative semantic graph of system resonance awareness.

Output:
  codex_symbolic_correlation.jsonl -> correlated entries for analysis.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

# Paths to relevant data sources
INSIGHT_LOG = Path("backend/logs/codex/codex_resonant_insight.jsonl")
TELEMETRY_LOG = Path("backend/logs/telemetry/coherence_tracker.jsonl")
OUTPUT_LOG = Path("backend/logs/codex/codex_symbolic_correlation.jsonl")

OUTPUT_LOG.parent.mkdir(parents=True, exist_ok=True)

def load_jsonl(path: Path, limit: int = 200):
    if not path.exists():
        return []
    with open(path, "r") as f:
        lines = f.readlines()[-limit:]
    records = []
    for l in lines:
        try:
            records.append(json.loads(l))
        except json.JSONDecodeError:
            continue
    return records

def correlate_symbolic_telemetry():
    """Correlate recent symbolic and telemetry entries."""
    symbolic = load_jsonl(INSIGHT_LOG)
    telemetry = load_jsonl(TELEMETRY_LOG)

    if not symbolic or not telemetry:
        print("[CodexTrace::C11] Insufficient data for correlation.")
        return None

    last_sym = symbolic[-1]
    recent_tel = telemetry[-5:]  # rolling window
    mean_phi = mean([t.get("Φ_stability_index", 0) for t in recent_tel])
    mean_pass = mean([t.get("rolling_avg_pass", 0) for t in recent_tel])

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": last_sym.get("symbolic_operator"),
        "ΔΦ": last_sym.get("ΔΦ"),
        "Δε": last_sym.get("Δε"),
        "κ": last_sym.get("prediction"),
        "Φ_mean": mean_phi,
        "pass_avg": mean_pass,
        "coherence_relation": abs(mean_phi - mean_pass),
        "correlated": abs(mean_phi - mean_pass) < 0.05,
    }

    with open(OUTPUT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    tag = "✅" if entry["correlated"] else "⚠"
    print(f"[CodexTrace::C11] {tag} {entry['symbol']} ↔ Φ_mean={mean_phi:.3f}, "
          f"ΔΦ={entry['ΔΦ']:+.4f}, coherence_relation={entry['coherence_relation']:.4f}")

    return entry

if __name__ == "__main__":
    print("🔗 Tessaris - CodexTrace Symbolic↔Telemetry Correlation Bridge")
    result = correlate_symbolic_telemetry()
    if result:
        print(json.dumps(result, indent=2))