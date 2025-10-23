#!/usr/bin/env python3
"""
📡 AION Resonance Telemetry Dashboard (Phase 32.7)
─────────────────────────────────────────────────
Streams live metrics from ResonanceTelemetry, GradientCorrectionLayer,
and Adaptive Drift Repair events. Displays:

• Drift (ΔΦ, Δε)
• Coherence (μ, κ)
• Reinforcement Strength & Decay
• Resonance Stability Index (RSI)
• Exploration (ε) and Neighborhood (k)
• 🩹 Drift-Repair Pulses (visual markers + console output)
• Optional stream logging → data/feedback/resonance_stream.jsonl
"""

import time
import json
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry
from backend.modules.aion_learning.gradient_correction_layer import GradientCorrectionLayer
from backend.modules.aion_feedback.resonance_stability_index import ResonanceStabilityIndex


class ResonanceDashboard:
    def __init__(self, interval: float = 0.5, max_points: int = 150,
                 save_path: str = "data/feedback/resonance_stream.jsonl"):
        self.telemetry = ResonanceTelemetry()
        self.grad = GradientCorrectionLayer()
        self.rsi_calc = ResonanceStabilityIndex()

        self.interval = interval
        self.max_points = max_points

        # rolling buffers
        self.history = {
            k: [] for k in [
                "ΔΦ", "Δε", "μ", "κ", "avg_strength",
                "decay_rate", "RSI", "ε", "k"
            ]
        }
        self.timestamps = []
        self.repair_indices = []

        # logging
        self.save_path = Path(save_path)
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

        # plotting
        plt.style.use("ggplot")
        self.fig, self.axs = plt.subplots(3, 1, figsize=(8, 8))
        self.fig.suptitle("🔵 AION Resonance Dashboard — RSI, ε, k & Drift-Repair Pulses")
        self._ani = None  # keep animation alive

    # ─────────────────────────────────────────────
    def append_event(self, event):
        """Append incoming telemetry or repair event."""
        try:
            metrics = event.get("data", event)
            metrics["avg_strength"] = self.grad.avg_strength
            metrics["decay_rate"] = self.grad.decay_rate

            # compute RSI
            try:
                rsi = self.rsi_calc.compute(metrics)
            except Exception:
                rsi = 0.0
            metrics["RSI"] = rsi

            ε = metrics.get("epsilon", None)
            k = metrics.get("k", None)

            # append
            self.timestamps.append(time.time())
            for key in ["ΔΦ", "Δε", "μ", "κ", "avg_strength", "decay_rate", "RSI"]:
                self.history[key].append(metrics.get(key, 0.0))
                if len(self.history[key]) > self.max_points:
                    self.history[key].pop(0)
            self.history["ε"].append(ε)
            self.history["k"].append(k)

            # drift-repair detection
            if event.get("event") == "drift_repair":
                self.repair_indices.append(len(self.history["RSI"]) - 1)
                print(f"🩹 Repair Pulse @ RSI={rsi:.3f}, ε={ε}, k={k}")

            # log
            with open(self.save_path, "a", buffering=1) as f:
                f.write(json.dumps(metrics) + "\n")

            # console RSI bar
            bar_len = int(rsi * 20)
            bar = "█" * bar_len + "-" * (20 - bar_len)
            print(f"RSI [{bar}] {rsi:.3f} | ε={ε} | k={k}")

        except Exception as e:
            print(f"⚠️ Telemetry parse error: {e}")

    # ─────────────────────────────────────────────
    def update_plot(self, _):
        """Update all subplots."""
        try:
            new_event = self.telemetry.emit()
            if new_event:
                self.append_event(new_event)
        except Exception as e:
            print(f"⚠️ Telemetry error: {e}")

        if not self.timestamps:
            return []

        t = np.arange(len(self.history["RSI"]))
        ax1, ax2, ax3 = self.axs

        # Drift & Coherence
        ax1.cla()
        ax1.plot(t, self.history["ΔΦ"], label="ΔΦ")
        ax1.plot(t, self.history["Δε"], label="Δε")
        ax1.plot(t, self.history["μ"], label="μ")
        ax1.plot(t, self.history["κ"], label="κ")
        ax1.set_title("Resonance Drift & Coherence")
        ax1.legend(loc="upper right"); ax1.grid(True)

        # Reinforcement / RSI
        ax2.cla()
        ax2.plot(t, self.history["RSI"], color="limegreen", label="RSI")
        for idx in self.repair_indices:
            if 0 <= idx < len(t):
                ax2.plot(t[idx], self.history["RSI"][idx], "rv", markersize=8)
        ax2.set_ylim(0, 1.05)
        ax2.legend(loc="upper right"); ax2.set_title("Resonance Stability Index (RSI)"); ax2.grid(True)

        # ε & k dynamics
        ax3.cla()
        ax3.plot(t, self.history["ε"], color="orange", label="ε (exploration)")
        ax3.plot(t, self.history["k"], color="skyblue", label="k (neighborhood)")
        ax3.legend(loc="upper right"); ax3.set_title("Exploration ε and Neighborhood k"); ax3.grid(True)

        plt.tight_layout()
        return self.axs

    # ─────────────────────────────────────────────
    def run(self):
        print("📡 Streaming RSI + ε + k telemetry (Ctrl + C to stop)")
        ani = FuncAnimation(self.fig, self.update_plot,
                            interval=int(self.interval * 1000),
                            cache_frame_data=False, save_count=2000)
        self._ani = ani  # prevent garbage collection

        import os
        if not os.environ.get("DISPLAY"):
            print("⚠️  No GUI display detected — running headless mode (text only).")
            try:
                while True:
                    self.update_plot(None)
                    if self.history["RSI"]:
                        rsi = self.history["RSI"][-1]
                        ε = self.history["ε"][-1]
                        k = self.history["k"][-1]
                        bar = "█" * int(rsi * 20) + "-" * (20 - int(rsi * 20))
                        print(f"RSI [{bar}] {rsi:.3f} | ε={ε} | k={k}")
                    time.sleep(self.interval)
            except KeyboardInterrupt:
                print("\n🛑 Headless telemetry loop stopped.")
        else:
            plt.show()


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    dashboard = ResonanceDashboard(interval=0.4)
    dashboard.run()