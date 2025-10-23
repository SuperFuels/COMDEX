#!/usr/bin/env python3
"""
📡 AION Resonance Telemetry Dashboard
─────────────────────────────────────
Streams live metrics from ResonanceTelemetry + GradientCorrectionLayer.
Displays drift (ΔΦ, Δε), coherence (μ, κ), reinforcement strength,
and Resonance Stability Index (RSI) in real time.
"""

import time
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry
from backend.modules.aion_learning.gradient_correction_layer import GradientCorrectionLayer
from backend.modules.aion_feedback.resonance_stability_index import ResonanceStabilityIndex


class ResonanceDashboard:
    def __init__(self, interval: float = 0.5, max_points: int = 100):
        self.telemetry = ResonanceTelemetry()
        self.grad = GradientCorrectionLayer()
        self.rsi_calc = ResonanceStabilityIndex()
        self.interval = interval
        self.max_points = max_points

        # time series buffers
        self.history = {
            k: [] for k in ["ΔΦ", "Δε", "μ", "κ", "avg_strength", "decay_rate", "RSI"]
        }
        self.timestamps = []

    # ─────────────────────────────────────────────
    # Core loop
    # ─────────────────────────────────────────────
    def run(self):
        plt.ion()
        fig, ax = plt.subplots(3, 1, figsize=(8, 8))
        (ax1, ax2, ax3) = ax

        print("📡 Streaming resonance telemetry + RSI (Ctrl+C to stop)")

        try:
            while True:
                packet = self.telemetry.emit()
                metrics = packet["data"]
                metrics["avg_strength"] = self.grad.avg_strength
                metrics["decay_rate"] = self.grad.decay_rate

                # Compute RSI
                rsi = self.rsi_calc.compute(metrics)
                metrics["RSI"] = rsi

                # Append new data
                self.timestamps.append(time.time())
                for k in self.history:
                    self.history[k].append(metrics.get(k, 0.0))
                    if len(self.history[k]) > self.max_points:
                        self.history[k].pop(0)

                # Create time axis
                t = np.arange(len(self.history["ΔΦ"]))

                # ───────────────────── Plot Resonance Metrics ─────────────────────
                ax1.cla()
                ax1.plot(t, self.history["ΔΦ"], label="ΔΦ")
                ax1.plot(t, self.history["Δε"], label="Δε")
                ax1.plot(t, self.history["μ"], label="μ")
                ax1.plot(t, self.history["κ"], label="κ")
                ax1.set_title("Resonance Drift & Coherence Metrics")
                ax1.legend(loc="upper right")
                ax1.grid(True)

                # ───────────────────── Plot Reinforcement Dynamics ─────────────────────
                ax2.cla()
                ax2.plot(t, self.history["avg_strength"], label="Avg Strength")
                ax2.plot(t, self.history["decay_rate"], label="Decay Rate")
                ax2.set_title("Reinforcement Strength / Decay")
                ax2.legend(loc="upper right")
                ax2.grid(True)

                # ───────────────────── Plot RSI (Stability Index) ─────────────────────
                ax3.cla()
                ax3.plot(t, self.history["RSI"], color="limegreen", label="RSI (Stability Index)")
                ax3.set_ylim(0, 1)
                ax3.set_title("Resonance Stability Index (RSI)")
                ax3.legend(loc="upper right")
                ax3.grid(True)

                plt.tight_layout()
                plt.pause(self.interval)

                # ───────────── Console RSI bar (for quick terminal readout) ─────────────
                bar_len = int(rsi * 20)
                bar = "█" * bar_len + "-" * (20 - bar_len)
                print(f"RSI [{bar}] {rsi:.3f}")

        except KeyboardInterrupt:
            print("\n🛑 Telemetry streaming stopped.")
            plt.ioff()
            plt.show()


if __name__ == "__main__":
    dashboard = ResonanceDashboard(interval=0.4)
    dashboard.run()