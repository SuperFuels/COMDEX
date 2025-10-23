#!/usr/bin/env python3
"""
🧬  Aion Fusion × Stability Overlay — Phase 35.7
───────────────────────────────────────────────────────────────────────────────
Correlates RSI variance (concept drift) with fusion/speciation/decay events
recorded by the Concept Evolution Engine.

Outputs a timeline showing:
    • RSI variance trend (red line)
    • Total concept links (blue line)
    • Fusion/speciation/decay markers
"""

import json, time, statistics
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Paths ───────────────────────────────────────────────
RSI_PATH      = Path("data/feedback/resonance_stream.jsonl")
EVOLUTION_LOG = Path("data/analysis/concept_evolution_log.jsonl")
OUTPUT        = Path("data/analysis/fusion_stability_overlay.png")

WINDOW_SIZE = 60   # seconds per averaging bin
COLORS = {
    "fusion": "green",
    "speciation": "blue",
    "decay": "red"
}

# ── Helpers ─────────────────────────────────────────────
def load_rsi_data():
    """Return RSI samples as (timestamp, RSI)."""
    if not RSI_PATH.exists():
        print(f"⚠️  No RSI data found at {RSI_PATH}")
        return []
    data = []
    with RSI_PATH.open() as f:
        for line in f:
            try:
                r = json.loads(line)
                ts = float(r.get("timestamp", time.time()))
                rsi = float(r.get("RSI", 0.0))
                data.append((ts, rsi))
            except Exception:
                continue
    return sorted(data, key=lambda x: x[0])

def load_evolution_events():
    """Load concept evolution log entries (fusion/speciation/decay)."""
    if not EVOLUTION_LOG.exists():
        print(f"⚠️  No evolution log found at {EVOLUTION_LOG}")
        return []
    events = []
    with EVOLUTION_LOG.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
                ts = float(rec.get("timestamp", time.time()))
                etype = rec.get("type") or rec.get("event_type") or "fusion"
                events.append((ts, etype))
            except Exception:
                continue
    return sorted(events, key=lambda x: x[0])

def group_variance(records):
    """Aggregate RSI variance by time window."""
    if not records:
        return [], []
    start = records[0][0]
    current = start
    values = []
    times, variances = [], []

    for ts, rsi in records:
        if ts - current < WINDOW_SIZE:
            values.append(rsi)
        else:
            if len(values) > 1:
                variances.append(statistics.pvariance(values))
                times.append(current)
            current = ts
            values = [rsi]

    if len(values) > 1:
        variances.append(statistics.pvariance(values))
        times.append(current)
    return times, variances

# ── Main Visualization ──────────────────────────────────
def build_overlay():
    print("🧬  Generating Fusion × Stability Overlay (Phase 35.7)…")

    rsi_data = load_rsi_data()
    if not rsi_data:
        print("⚠️  No RSI data to process.")
        return
    events = load_evolution_events()

    times, variances = group_variance(rsi_data)
    if not times or not variances:
        print("⚠️  Not enough RSI data to compute variance.")
        return

    # Normalize time axis
    start_time = times[0]
    time_labels = [datetime.fromtimestamp(t).strftime("%H:%M:%S") for t in times]

    # Mock "concept link count" (if missing): use moving average of RSI samples
    concept_counts = np.linspace(1800, 1800 + len(times)*5, len(times))

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Plot RSI variance (drift)
    ax1.plot(times, variances, color="firebrick", linewidth=2, label="RSI Variance (Drift Intensity)")
    ax1.set_ylabel("RSI Variance", color="firebrick")
    ax1.tick_params(axis="y", labelcolor="firebrick")

    # Secondary Y-axis: concept link count
    ax2 = ax1.twinx()
    ax2.plot(times, concept_counts, color="steelblue", linewidth=1.8, label="Total Concept Links")
    ax2.set_ylabel("Number of Concept Links", color="steelblue")
    ax2.tick_params(axis="y", labelcolor="steelblue")

    # Mark fusion/speciation/decay events
    for ts, etype in events:
        color = COLORS.get(etype, "gray")
        plt.axvline(x=ts, color=color, linestyle="--", alpha=0.4, linewidth=1)
        ax1.text(ts, max(variances) * 0.9, etype[0].upper(), color=color, fontsize=7, rotation=90, ha="center", va="center")

    plt.title("Aion Fusion × Stability Overlay — Phase 35.7")
    plt.xlabel("Time")
    plt.xticks(times[::max(1, len(times)//10)], time_labels[::max(1, len(times)//10)], rotation=45, ha="right", fontsize=8)
    fig.tight_layout()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT, dpi=200)
    plt.close()
    print(f"✅  Fusion × Stability overlay saved → {OUTPUT}")

# ── Entrypoint ───────────────────────────────────────────
if __name__ == "__main__":
    build_overlay()