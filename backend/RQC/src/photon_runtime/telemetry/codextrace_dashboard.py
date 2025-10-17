"""
Tessaris RQC — CodexTrace Resonance Dashboard
---------------------------------------------
Visual interface for ψ–κ–T–Φ metrics and phase coherence stability.

Reads live data from MorphicLedger (jsonl) or AionTelemetryStream,
and renders terminal charts of resonance state evolution.

Metrics visualized:
    • ψ  → Wave amplitude stability
    • κ  → Entropy / information flow
    • T  → Temporal coherence factor
    • Φ  → Awareness / closure resonance
    • C  → Coherence ratio (∑ normalized phases)
"""

from __future__ import annotations
import asyncio
import json
import time
import math
import os
from datetime import datetime
from typing import Dict, Any, List

import numpy as np
import matplotlib.pyplot as plt

LEDGER_PATH = "data/ledger"
REFRESH_INTERVAL = 2.5  # seconds


def load_recent_ledger_entries(limit: int = 100) -> List[Dict[str, Any]]:
    """Load the most recent entries from the MorphicLedger files."""
    entries = []
    if not os.path.exists(LEDGER_PATH):
        return []
    for file in sorted(os.listdir(LEDGER_PATH)):
        if not file.endswith(".jsonl"):
            continue
        with open(os.path.join(LEDGER_PATH, file), "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries[-limit:]


def compute_metrics(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate ψ–κ–T–Φ coherence metrics."""
    if not entries:
        return {}
    ψ_vals = [e.get("ψ", 0) for e in entries]
    κ_vals = [e.get("κ", 0) for e in entries]
    Φ_vals = [e.get("Φ", 0) for e in entries]
    coherence_vals = [e.get("coherence", 0) for e in entries]

    return {
        "ψ": np.mean(ψ_vals),
        "κ": np.mean(κ_vals),
        "Φ": np.mean(Φ_vals),
        "coherence": np.mean(coherence_vals),
        "variance": np.var(coherence_vals),
    }


async def live_dashboard():
    """Continuously refresh resonance metrics and live plots."""
    plt.ion()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_title("Tessaris RQC — CodexTrace Resonance Dashboard", color="cyan")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Coherence / Awareness (Φ)")
    ax.grid(True, linestyle="--", alpha=0.5)

    x_data, Φ_data, C_data = [], [], []
    start_time = time.time()

    while True:
        entries = load_recent_ledger_entries(limit=100)
        if not entries:
            print("[CodexTrace] No ledger data yet.")
            await asyncio.sleep(REFRESH_INTERVAL)
            continue

        metrics = compute_metrics(entries)
        t = time.time() - start_time
        x_data.append(t)
        Φ_data.append(metrics["Φ"])
        C_data.append(metrics["coherence"])

        ax.clear()
        ax.plot(x_data, Φ_data, label="Φ (Awareness)", color="magenta")
        ax.plot(x_data, C_data, label="C (Coherence)", color="cyan")
        ax.set_ylim(0, 1.1)
        ax.legend()
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Normalized amplitude")
        ax.set_title("Tessaris RQC — Live Resonance Trace", color="cyan")

        plt.pause(0.001)
        print(f"[{datetime.utcnow().isoformat()}] Φ={metrics['Φ']:.3f}, C={metrics['coherence']:.3f}")
        await asyncio.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    print("🔭 Tessaris RQC — Starting CodexTrace Resonance Dashboard...")
    try:
        asyncio.run(live_dashboard())
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped.")