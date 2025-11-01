# ===============================
# 📁 backend/quant/qplot/qplot_metrics.py
# ===============================
"""
📈 QPlotMetrics - Visualization & Analysis Tools
-------------------------------------------------
Provides plotting utilities for Q-Series runtime metrics.
Supports static Matplotlib rendering and headless export for telemetry dashboards.

Main Functions:
    plot_resonance_timeseries(history)
    plot_entropy_harmony(history)
    plot_coherence_map(metrics)
    export_all_plots(metrics, out_dir="backend/qplot/exports")
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import matplotlib.pyplot as plt


# ----------------------------------------------------------------------
def plot_resonance_timeseries(history: List[Dict[str, Any]], show: bool = False):
    """
    🌀 Plot Φ-ψ resonance evolution over time.
    """
    if not history:
        return None

    t = [i for i in range(len(history))]
    Φ = [h.get("Φ_mean", 0.0) for h in history]
    ψ = [h.get("ψ_mean", 0.0) for h in history]
    coherence = [h.get("coherence_index", 0.0) for h in history]

    plt.figure(figsize=(8, 5))
    plt.plot(t, Φ, label="Φ_mean")
    plt.plot(t, ψ, label="ψ_mean")
    plt.plot(t, coherence, label="Coherence Index", linestyle="--")
    plt.xlabel("Run #")
    plt.ylabel("Resonance Magnitude")
    plt.title("Φ-ψ Resonance Evolution")
    plt.legend()
    plt.grid(True, alpha=0.3)
    if show:
        plt.show()
    return plt.gcf()


# ----------------------------------------------------------------------
def plot_entropy_harmony(history: List[Dict[str, Any]], show: bool = False):
    """
    🎵 Plot Entropy vs Harmony vs Novelty.
    """
    if not history:
        return None

    t = [i for i in range(len(history))]
    entropy = [h.get("entropy_mean", 0.0) for h in history]
    harmony = [h.get("harmony_mean", 0.0) for h in history]
    novelty = [h.get("novelty_mean", 0.0) for h in history]

    plt.figure(figsize=(8, 5))
    plt.plot(t, entropy, label="Entropy", color="tab:red")
    plt.plot(t, harmony, label="Harmony", color="tab:blue")
    plt.plot(t, novelty, label="Novelty", color="tab:green")
    plt.xlabel("Run #")
    plt.ylabel("E7 Metric Value")
    plt.title("E7 Metrics - Entropy / Harmony / Novelty")
    plt.legend()
    plt.grid(True, alpha=0.3)
    if show:
        plt.show()
    return plt.gcf()


# ----------------------------------------------------------------------
def plot_coherence_map(metrics: Dict[str, Any], show: bool = False):
    """
    🌌 Visualize coherence energy and SQI in 2-D phase space.
    """
    import numpy as np
    coh = [m.get("coherence_mean", 0.0) for m in metrics.values()]
    sqi = [m.get("sqi_mean", 0.0) for m in metrics.values()]

    plt.figure(figsize=(6, 6))
    plt.scatter(coh, sqi, c=sqi, cmap="viridis", s=60, alpha=0.7)
    plt.xlabel("Coherence Mean")
    plt.ylabel("SQI Mean")
    plt.title("Coherence-SQI Phase Map")
    plt.grid(True, alpha=0.3)
    if show:
        plt.show()
    return plt.gcf()


# ----------------------------------------------------------------------
def export_all_plots(metrics_obj, out_dir: str = "backend/qplot/exports") -> List[str]:
    """
    📦 Export all standard plots to PNG for telemetry archive.
    Returns list of written file paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    history = metrics_obj.history
    filenames = []

    # Φ-ψ resonance
    fig1 = plot_resonance_timeseries(history)
    p1 = os.path.join(out_dir, f"resonance_timeseries_{datetime.utcnow().strftime('%H%M%S')}.png")
    fig1.savefig(p1, dpi=160)
    filenames.append(p1)
    plt.close(fig1)

    # E7 metrics
    fig2 = plot_entropy_harmony(history)
    p2 = os.path.join(out_dir, f"entropy_harmony_{datetime.utcnow().strftime('%H%M%S')}.png")
    fig2.savefig(p2, dpi=160)
    filenames.append(p2)
    plt.close(fig2)

    # Coherence map (if multiple summaries)
    if len(history) > 2:
        metrics_map = {f"run_{i}": h for i, h in enumerate(history)}
        fig3 = plot_coherence_map(metrics_map)
        p3 = os.path.join(out_dir, f"coherence_map_{datetime.utcnow().strftime('%H%M%S')}.png")
        fig3.savefig(p3, dpi=160)
        filenames.append(p3)
        plt.close(fig3)

    return filenames