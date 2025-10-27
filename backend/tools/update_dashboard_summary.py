#!/usr/bin/env python3
"""
📊 AION Live Dashboard Aggregator — Phase 56 Systemic Resonant Synchronization
──────────────────────────────────────────────────────────────────────────────
Collects and summarizes live resonance events and synchronizes Θ-phases
across all active engines.

New Features:
  • Θ.sync_all() → aligns local heartbeat frequencies + entropy drift
  • Harmony Score metric:
        H = 1 - (1/n) * Σ |Θᵢ − Θ_master|
  • Aggregated stream telemetry:
        - plan_eval
        - phase_shift (ethical reconsiderations)
        - resonance_tension (goal alignment drift)

Outputs → data/analysis/aion_live_dashboard.json
"""

import json
import math
from pathlib import Path
from statistics import fmean, StatisticsError
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

# Global Θ controller (master phase anchor)
Theta = ResonanceHeartbeat(namespace="global_theta")

LOG = Path("data/analysis/aion_live_dashboard.jsonl")
OUT = Path("data/analysis/aion_live_dashboard.json")
STREAMS = ["plan_eval", "phase_shift", "resonance_tension"]


# ---------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------
def safe_mean(values):
    try:
        return round(fmean(values), 3)
    except (StatisticsError, ZeroDivisionError):
        return None


def compute_harmony(phases):
    """Compute Harmony Score from list of Θ frequencies."""
    if not phases:
        return None
    master = fmean(phases)
    diffs = [abs(p - master) for p in phases]
    H = 1 - (sum(diffs) / len(phases))
    return round(max(0.0, min(1.0, H)), 3)


# ---------------------------------------------------------------------
# Θ.sync_all — Phase synchronization
# ---------------------------------------------------------------------
def sync_all_engines():
    """
    Scans for all active heartbeat snapshot files and synchronizes them.
    Returns list of engine phases and the harmony score.
    """
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

    # Compute harmony score before sync
    harmony = compute_harmony(phases)

    # Perform sync — normalize each heartbeat file toward global master
    if phases:
        master_freq = fmean(phases)
        for f in hb_files:
            try:
                js = json.loads(f.read_text())
                js["Θ_frequency"] = round(master_freq, 3)
                f.write_text(json.dumps(js, indent=2))
            except Exception:
                pass

        Theta.tick()  # emit master Θ pulse post-sync

    return phases, harmony


# ---------------------------------------------------------------------
# Dashboard Aggregation
# ---------------------------------------------------------------------
def main():
    if not LOG.exists():
        print("No dashboard log yet.")
        return

    rows = []
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
        print("⚠️ No valid events in dashboard log.")
        return

    # Group by stream type
    groups = {s: [] for s in STREAMS}
    for r in rows:
        evt = r.get("event") or r.get("type") or r.get("name")
        if evt in groups:
            groups[evt].append(r)

    # Aggregate stream metrics
    summary = {
        "events_total": len(rows),
        "streams": {},
        "last_event": rows[-1] if rows else None,
    }

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

    # -----------------------------------------------------------------
    # Phase 56 — Global Synchronization + Harmony Score
    # -----------------------------------------------------------------
    phases, harmony = sync_all_engines()
    summary["engine_phases"] = phases
    summary["harmony_score"] = harmony

    # Save output
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))
    print("📤 Wrote synchronized dashboard summary →", OUT)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()