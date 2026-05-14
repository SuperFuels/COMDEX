#!/usr/bin/env python3
"""
🌀  Aion Live Evolution Dashboard - Phase 35.5 (Stable Runtime)
─────────────────────────────────────────────────────────────────────
Continuously updates concept evolution and RSI variance in real time.
Works both with and without GUI (headless safe).
"""

import json, time, statistics
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # headless mode safe
import matplotlib.pyplot as plt

# ── Paths ───────────────────────────────────────────────
SNAPSHOT_PATH = Path("data/feedback/concept_evolution_snapshot.jsonl")
REINFORCE_LOG = Path("data/feedback/concept_reinforcement.log")
RSI_STREAM    = Path("data/feedback/resonance_stream.jsonl")
OUTPUT_PLOT   = Path("data/analysis/concept_evolution_live.png")

REFRESH_INTERVAL = 5.0
WINDOW_SIZE = 100

# ── Loaders ─────────────────────────────────────────────
def load_jsonl(path):
    if not path.exists():
        return []
    data = []
    with path.open() as f:
        for line in f:
            try:
                data.append(json.loads(line.strip()))
            except Exception:
                continue
    return data

def load_snapshots():
    return load_jsonl(SNAPSHOT_PATH)

def load_reinforcements():
    if not REINFORCE_LOG.exists():
        return []
    ev = []
    with REINFORCE_LOG.open() as f:
        for line in f:
            try:
                ts = float(line.split()[0])
                ev.append(datetime.fromtimestamp(ts))
            except Exception:
                continue
    return ev

def load_rsi_variance():
    if not RSI_STREAM.exists():
        return []
    vals, times = [], []
    with RSI_STREAM.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
                if "RSI" in rec and rec.get("timestamp"):
                    vals.append(rec["RSI"])
                    times.append(rec["timestamp"])
            except Exception:
                continue
    if not vals:
        return []
    series = []
    for i in range(0, len(vals), WINDOW_SIZE):
        win = vals[i:i + WINDOW_SIZE]
        tw  = times[i:i + WINDOW_SIZE]
        if win and tw:
            var = statistics.pvariance(win)
            mean_t = statistics.mean(tw)
            series.append((datetime.fromtimestamp(mean_t), var))
    return series

# ── Update cycle ────────────────────────────────────────
def update_plot():
    snaps = load_snapshots()
    if not snaps:
        print("⚠️  No snapshot data yet.")
        return
    times = [datetime.fromtimestamp(s["timestamp"]) for s in snaps]
    counts = [sum(s["concepts"].values()) for s in snaps]

    plt.figure(figsize=(10,5))
    ax1 = plt.gca()
    ax2 = ax1.twinx()

    ax1.plot(times, counts, "o-", color="tab:blue", label="Total Concept Links")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Concept Links", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")

    # RSI overlay
    rsi_series = load_rsi_variance()
    if rsi_series:
        t2, v2 = zip(*rsi_series)
        ax2.plot(t2, v2, "-", color="tab:red", alpha=0.6, label="Mean RSI Variance")
        ax2.set_ylabel("RSI Variance", color="tab:red")
        ax2.tick_params(axis="y", labelcolor="tab:red")

    # Reinforcement markers
    reinf = load_reinforcements()
    if reinf:
        ymin, ymax = ax1.get_ylim()
        for r in reinf:
            ax1.vlines(r, ymin, ymax, color="green", alpha=0.1)
        ax1.text(times[-1], ymax * 0.95, f"Reinforcement: {len(reinf)}", color="green", fontsize=8)

    plt.title("Aion Concept Evolution - Phase 35.5 (Live Stream)")
    plt.tight_layout()
    OUTPUT_PLOT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PLOT)
    plt.close()

    # CLI ticker
    latest_ct = counts[-1] if counts else 0
    latest_rsi = rsi_series[-1][1] if rsi_series else 0
    print(f"⏱️  {datetime.now().strftime('%H:%M:%S')} | Links: {latest_ct} | RSI Var: {latest_rsi:.5f}")

# ── Main Loop ───────────────────────────────────────────
if __name__ == "__main__":
    print("🌀  Launching Aion Live Evolution Dashboard (Phase 35.5 - Headless Safe)...")
    while True:
        try:
            update_plot()
            time.sleep(REFRESH_INTERVAL)
        except KeyboardInterrupt:
            print("\n🛑  Live evolution stream stopped by user.")
            break