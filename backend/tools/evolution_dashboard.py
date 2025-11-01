#!/usr/bin/env python3
"""
📊  Aion Evolution Dashboard - Phase 35.4
───────────────────────────────────────────────────────────────────────────────
Visualizes concept evolution and overlays RSI variance stability.

Inputs:
  * data/feedback/concept_evolution_snapshot.jsonl
  * data/feedback/concept_reinforcement.log   (optional)
  * data/feedback/resonance_stream.jsonl      (RSI variance overlay)

Outputs:
  * data/analysis/concept_evolution_plot.png
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime
import statistics

# ── File paths ───────────────────────────────────────
SNAPSHOT_PATH = Path("data/feedback/concept_evolution_snapshot.jsonl")
REINFORCE_LOG = Path("data/feedback/concept_reinforcement.log")
RSI_STREAM    = Path("data/feedback/resonance_stream.jsonl")
OUTPUT_PLOT   = Path("data/analysis/concept_evolution_plot.png")


# ── Loaders ──────────────────────────────────────────
def load_snapshots():
    if not SNAPSHOT_PATH.exists():
        print("⚠️  No snapshot file found:", SNAPSHOT_PATH)
        return []
    data = []
    with SNAPSHOT_PATH.open() as f:
        for line in f:
            try:
                rec = json.loads(line.strip())
                data.append(rec)
            except json.JSONDecodeError:
                continue
    return data


def load_reinforcements():
    if not REINFORCE_LOG.exists():
        return []
    events = []
    with REINFORCE_LOG.open() as f:
        for line in f:
            try:
                ts = float(line.split()[0])
                events.append(datetime.fromtimestamp(ts))
            except Exception:
                continue
    return events


def load_rsi_variance():
    """Compute global RSI variance across recent telemetry."""
    if not RSI_STREAM.exists():
        print("⚠️  No RSI telemetry found.")
        return []
    window, by_time = 100, []
    with RSI_STREAM.open() as f:
        batch, timestamps = [], []
        for line in f:
            try:
                rec = json.loads(line)
                rsi = rec.get("RSI")
                t = rec.get("timestamp") or rec.get("t")
                if rsi is not None and isinstance(rsi, (int, float)):
                    batch.append(rsi)
                    timestamps.append(t or 0)
                    if len(batch) >= window:
                        mean_t = statistics.mean(timestamps)
                        var = statistics.pvariance(batch)
                        by_time.append((mean_t, var))
                        batch.clear()
                        timestamps.clear()
            except Exception:
                continue
    return [(datetime.fromtimestamp(t), v) for t, v in by_time if t > 0]


# ── Plot ─────────────────────────────────────────────
def plot_evolution():
    snaps = load_snapshots()
    if not snaps:
        print("⚠️  No data to plot.")
        return

    times = [datetime.fromtimestamp(s["timestamp"]) for s in snaps]
    concept_counts = [sum(s["concepts"].values()) for s in snaps]

    plt.figure(figsize=(10, 5))
    ax1 = plt.gca()
    ax1.plot(times, concept_counts, "o-", label="Total Concept Links", color="tab:blue")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Number of Concept Links", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.grid(True, alpha=0.3)

    # RSI variance overlay (secondary axis)
    rsi_series = load_rsi_variance()
    if rsi_series:
        ax2 = ax1.twinx()
        t2, v2 = zip(*rsi_series)
        ax2.plot(t2, v2, "-", color="tab:red", alpha=0.6, label="Mean RSI Variance")
        ax2.set_ylabel("RSI Variance", color="tab:red")
        ax2.tick_params(axis="y", labelcolor="tab:red")
        ax2.legend(loc="upper left")

    # Reinforcement markers
    reinf = load_reinforcements()
    if reinf:
        ymin, ymax = ax1.get_ylim()
        for r in reinf:
            ax1.vlines(r, ymin, ymax, color="green", alpha=0.1)
        ax1.text(times[-1], ymax * 0.95,
                 f"Reinforcement events: {len(reinf)}",
                 fontsize=8, color="green")

    plt.title("Aion Concept Evolution - Phase 35.4 (RSI Variance Overlay)")
    plt.tight_layout()
    OUTPUT_PLOT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PLOT)
    print(f"✅  Evolution plot with RSI overlay saved -> {OUTPUT_PLOT}")


# ── Entry ────────────────────────────────────────────
if __name__ == "__main__":
    print("📊  Launching Aion Evolution Dashboard (Phase 35.4)...")
    plot_evolution()