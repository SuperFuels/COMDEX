# ──────────────────────────────────────────────
#  Tessaris • HQCE Telemetry Viewer (Stage 9)
#  Visualizes ψ–κ–T + coherence evolution over time
#  Supports static and live modes from MorphicLedger
# ──────────────────────────────────────────────

import os
import sys
import time
import json
import argparse
import matplotlib.pyplot as plt
from typing import List, Dict, Any

from backend.modules.holograms.morphic_ledger import morphic_ledger


def load_entries(path: str) -> List[Dict[str, Any]]:
    """Load ledger JSONL entries."""
    if not os.path.exists(path):
        print(f"[!] Ledger not found at {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def plot_metrics(entries: List[Dict[str, Any]]):
    """Plot ψ–κ–T–C metrics from ledger."""
    if not entries:
        print("[!] No entries to plot.")
        return

    timestamps = [e["timestamp"] for e in entries]
    ψ_vals = [e["tensor"]["psi"] for e in entries]
    κ_vals = [e["tensor"]["kappa"] for e in entries]
    C_vals = [e["tensor"]["coherence"] for e in entries]
    T_vals = [e["tensor"]["T"] for e in entries]

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, ψ_vals, label="ψ (Entropy)")
    plt.plot(timestamps, κ_vals, label="κ (Curvature)")
    plt.plot(timestamps, C_vals, label="C (Coherence)")
    plt.plot(timestamps, T_vals, label="T (Temporal Flux)")
    plt.title("HQCE ψ–κ–T–C Telemetry Trend")
    plt.xlabel("Time (s)")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def live_watch(path: str, interval: float = 2.0):
    """Continuously watch and refresh live telemetry plot."""
    print(f"[HQCE] Live telemetry watching {path} (interval={interval}s) ... Ctrl-C to exit.")
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 6))
    while True:
        entries = load_entries(path)[-100:]
        if not entries:
            time.sleep(interval)
            continue

        ψ_vals = [e["tensor"]["psi"] for e in entries]
        κ_vals = [e["tensor"]["kappa"] for e in entries]
        C_vals = [e["tensor"]["coherence"] for e in entries]
        T_vals = [e["tensor"]["T"] for e in entries]
        x = list(range(len(entries)))

        ax.clear()
        ax.plot(x, ψ_vals, label="ψ")
        ax.plot(x, κ_vals, label="κ")
        ax.plot(x, C_vals, label="C")
        ax.plot(x, T_vals, label="T")
        ax.set_title("Live HQCE Telemetry (ψ–κ–T–C)")
        ax.legend()
        ax.grid(True)
        plt.pause(interval)


def print_summary(entries: List[Dict[str, Any]]):
    """Print recent telemetry statistics."""
    if not entries:
        print("[!] No data to summarize.")
        return
    from statistics import mean, pstdev
    ψ = [e["tensor"]["psi"] for e in entries]
    κ = [e["tensor"]["kappa"] for e in entries]
    C = [e["tensor"]["coherence"] for e in entries]
    print("────────────────────────────────────────────")
    print(f"ψ_mean={mean(ψ):.3f}  κ_mean={mean(κ):.3f}  C_mean={mean(C):.3f}")
    print(f"ψ_std ={pstdev(ψ) if len(ψ)>1 else 0:.4f}  C_std ={pstdev(C) if len(C)>1 else 0:.4f}")
    print(f"Stability Index ≈ {1 - (pstdev(C) if len(C)>1 else 0):.3f}")
    print(f"Total Entries: {len(entries)}")
    print("────────────────────────────────────────────")


def main():
    parser = argparse.ArgumentParser(description="HQCE Telemetry Viewer")
    parser.add_argument("--path", type=str, default=morphic_ledger.ledger_path, help="Path to ledger JSONL")
    parser.add_argument("--live", action="store_true", help="Enable live monitoring mode")
    parser.add_argument("--summary", action="store_true", help="Print summary instead of plot")
    args = parser.parse_args()

    entries = load_entries(args.path)
    if args.summary:
        print_summary(entries)
    elif args.live:
        live_watch(args.path)
    else:
        plot_metrics(entries)


if __name__ == "__main__":
    main()