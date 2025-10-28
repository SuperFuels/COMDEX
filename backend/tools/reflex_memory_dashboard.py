#!/usr/bin/env python3
"""
📊 ReflexMemory Metrics Dashboard — R7 Appendix Exporter
───────────────────────────────────────────────────────────────
Analyzes ReflexMemory and ActionSwitch telemetry to compute:
  • Success rate and violation frequency
  • Average Θ coherence and ΔΦ drift
  • SQI history evolution
  • Reflex efficiency index (REI)
Outputs → data/analysis/reflex_memory_dashboard.json
"""

import json, time, math
from pathlib import Path
from statistics import fmean, StatisticsError

TRACE_PATH = Path("data/telemetry/action_switch_trace.json")
OUT_PATH = Path("data/analysis/reflex_memory_dashboard.json")

def safe_mean(values):
    try:
        return round(fmean(values), 3)
    except (StatisticsError, ZeroDivisionError):
        return None

def main():
    if not TRACE_PATH.exists():
        print("⚠️ No reflex telemetry trace found.")
        return

    entries = []
    with open(TRACE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    if not entries:
        print("⚠️ No valid reflex entries found.")
        return

    successes = [e for e in entries if e.get("allowed")]
    failures  = [e for e in entries if not e.get("allowed")]

    thetas = [e.get("theta", 0.0) for e in entries]
    vio_counts = [e.get("violations", 0) for e in entries]
    drift_vals = [abs(e.get("theta", 0.0) - safe_mean(thetas)) for e in entries if e.get("theta")]

    rei = round((len(successes) / len(entries)) * (1 - safe_mean(drift_vals or [0])), 3)

    summary = {
        "total_actions": len(entries),
        "success_rate": round(len(successes) / len(entries), 3),
        "avg_theta": safe_mean(thetas),
        "avg_drift": safe_mean(drift_vals),
        "avg_violations": safe_mean(vio_counts),
        "reflex_efficiency_index": rei,
        "last_action": entries[-1] if entries else None
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, indent=2))
    print(f"📤 ReflexMemory dashboard written → {OUT_PATH}")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()