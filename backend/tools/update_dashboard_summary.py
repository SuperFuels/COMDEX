#!/usr/bin/env python3
"""
📊 AION Live Dashboard Aggregator — Phase 57a Dynamic Resonance Drift Compensation
──────────────────────────────────────────────────────────────────────────────
Extends systemic Θ-synchronization with ΔΦ drift monitoring and correction metrics.

New in Phase 57a:
  • Integrates "drift_corrected" telemetry from ResonanceHeartbeat.monitor_drift()
  • Reads resonant_drift_log.jsonl for ΔΦ correction events
  • Adds drift summary: total corrections + average ΔΦ deviation
  • Retains Phase 56 Harmony Score & per-engine Θ synchronization

Outputs → data/analysis/aion_live_dashboard.json
"""

import json
import math
from pathlib import Path
from statistics import fmean, StatisticsError
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

# Global Θ controller
Theta = ResonanceHeartbeat(namespace="global_theta")

LOG = Path("data/analysis/aion_live_dashboard.jsonl")
DRIFT_LOG = Path("data/aion_field/resonant_drift_log.jsonl")
OUT = Path("data/analysis/aion_live_dashboard.json")

# Extended telemetry streams
STREAMS = ["plan_eval", "phase_shift", "resonance_tension", "drift_corrected"]

# ---------------------------------------------------------------------
def safe_mean(values):
    try:
        return round(fmean(values), 3)
    except (StatisticsError, ZeroDivisionError):
        return None


def compute_harmony(phases):
    if not phases:
        return None
    master = fmean(phases)
    diffs = [abs(p - master) for p in phases]
    H = 1 - (sum(diffs) / len(phases))
    return round(max(0.0, min(1.0, H)), 3)


# ---------------------------------------------------------------------
# Θ-sync & drift coupling
# ---------------------------------------------------------------------
def sync_all_engines():
    hb_dir = Path("data/aion_field")
    hb_files = list(hb_dir.glob("*heartbeat_live.json"))
    phases = []

    for f in hb_files:
        try:
            js = json.loads(f.read_text())
            freq = float(js.get("Θ_frequency", 1.0))
            phases.append(freq)
        except Exception:
            continue

    harmony = compute_harmony(phases)
    if phases:
        master_freq = fmean(phases)
        for f in hb_files:
            try:
                js = json.loads(f.read_text())
                js["Θ_frequency"] = round(master_freq, 3)
                f.write_text(json.dumps(js, indent=2))
            except Exception:
                pass
        Theta.tick()

    return phases, harmony


# ---------------------------------------------------------------------
# Main dashboard aggregation
# ---------------------------------------------------------------------
def main():
    rows = []
    if LOG.exists():
        with open(LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    js = json.loads(line)
                    rows.append(js)
                except Exception:
                    continue

    if not rows:
        print("⚠️ No valid dashboard events.")
        return

    groups = {s: [] for s in STREAMS}
    for r in rows:
        evt = r.get("event") or r.get("type") or r.get("name")
        if evt in groups:
            groups[evt].append(r)

    summary = {
        "events_total": len(rows),
        "streams": {},
        "last_event": rows[-1] if rows else None,
    }

    # Stream aggregates
    for name, items in groups.items():
        if not items:
            continue
        if name == "plan_eval":
            sqis = [i.get("sqi") for i in items if isinstance(i.get("sqi"), (int, float))]
            ents = [i.get("entropy") for i in items if isinstance(i.get("entropy"), (int, float))]
            summary["streams"][name] = {
                "count": len(items),
                "avg_SQI": safe_mean(sqis),
                "avg_entropy": safe_mean(ents),
            }
        elif name == "phase_shift":
            confs = [i.get("confidence") for i in items if isinstance(i.get("confidence"), (int, float))]
            summary["streams"][name] = {
                "count": len(items),
                "avg_confidence": safe_mean(confs),
            }
        elif name == "resonance_tension":
            deltas = [i.get("delta") for i in items if isinstance(i.get("delta"), (int, float))]
            summary["streams"][name] = {
                "count": len(items),
                "avg_delta": safe_mean(deltas),
            }
        elif name == "drift_corrected":
            drifts = [i.get("ΔΦ") for i in items if isinstance(i.get("ΔΦ"), (int, float))]
            summary["streams"][name] = {
                "count": len(items),
                "avg_ΔΦ": safe_mean(drifts),
            }

    # -----------------------------------------------------------------
    # Phase 56–57 synchronization and drift data
    # -----------------------------------------------------------------
    phases, harmony = sync_all_engines()
    summary["engine_phases"] = phases
    summary["harmony_score"] = harmony

    # Include drift log review
    drift_rows = []
    if DRIFT_LOG.exists():
        with open(DRIFT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    drift_rows.append(json.loads(line))
                except Exception:
                    continue

    if drift_rows:
        deltas = [r.get("ΔΦ") for r in drift_rows if isinstance(r.get("ΔΦ"), (int, float))]
        summary["drift_monitor"] = {
            "total_corrections": len(drift_rows),
            "avg_ΔΦ": safe_mean(deltas),
            "last_correction": drift_rows[-1],
        }

    # -----------------------------------------------------------------
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))
    print("📤 Wrote synchronized dashboard summary →", OUT)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()