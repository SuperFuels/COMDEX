#!/usr/bin/env python3
"""
Tessaris * SLE Telemetry Viewer
──────────────────────────────────────────────
Loads telemetry exports (sle_validation_*.json)
and plots coherence (qscore) evolution over time.

Usage:
    PYTHONPATH=. python backend/scripts/view_telemetry.py
"""

import os
import json
import matplotlib.pyplot as plt
from glob import glob
from datetime import datetime

EXPORT_DIR = "./exports/telemetry"

def load_latest_report():
    """Load the most recent sle_validation_*.json file."""
    files = sorted(glob(os.path.join(EXPORT_DIR, "sle_validation_*.json")))
    if not files:
        print("⚠️ No telemetry files found in ./exports/telemetry")
        return None
    latest = files[-1]
    print(f"📄 Loading telemetry: {latest}")
    with open(latest, "r") as f:
        return json.load(f)

def plot_qscores(report):
    """Plot qscore (coherence) evolution from telemetry data."""
    metrics = report.get("metrics", [])
    if not metrics:
        print("⚠️ No metrics found in report.")
        return

    timestamps = [m["timestamp"] for m in metrics if "timestamp" in m]
    qscores = [m["qscore"] for m in metrics if "qscore" in m]
    times = [datetime.fromtimestamp(t) for t in timestamps]

    plt.figure(figsize=(10, 5))
    plt.plot(times, qscores, marker="o", linewidth=2)
    plt.title("SLE Coherence (qscore) Evolution")
    plt.xlabel("Timestamp")
    plt.ylabel("qscore (Coherence)")
    plt.grid(True, alpha=0.3)

    threshold = report.get("closure_report", {}).get("threshold", 0.8)
    plt.axhline(y=threshold, color="red", linestyle="--", alpha=0.6, label=f"πs Threshold {threshold}")
    plt.legend()
    plt.tight_layout()
    plt.show()

def summarize(report):
    """Print summary statistics to console."""
    closure_ok = report.get("closure_ok", False)
    session_id = report.get("session_id", "unknown")
    avg_q = sum([m.get("qscore", 0.0) for m in report.get("metrics", [])]) / max(1, len(report.get("metrics", [])))
    print("───────────────────────────────────────")
    print(f"Session ID: {session_id}")
    print(f"πs Closure: {'✅ Stable' if closure_ok else '⚠️ Incomplete'}")
    print(f"Average Coherence: {avg_q:.3f}")
    print("───────────────────────────────────────")

def main():
    report = load_latest_report()
    if not report:
        return
    summarize(report)
    plot_qscores(report)

if __name__ == "__main__":
    main()