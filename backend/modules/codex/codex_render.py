# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v1.2 — CodexRender Visualization Engine
# Unified telemetry ingestion and visualization for λ–ψ–E feedback
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v1.2.1 — October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
import os
import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional

import numpy as np
import matplotlib.pyplot as plt


# ──────────────────────────────────────────────────────────────
# CodexRender Telemetry Aggregator
# ──────────────────────────────────────────────────────────────
class TelemetryBuffer:
    """Thread-safe buffer for incoming telemetry events."""

    def __init__(self, maxlen: int = 5000):
        self.events = deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def append(self, event: Dict[str, Any]):
        with self.lock:
            self.events.append(event)

    def snapshot(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.events)


telemetry_buffer = TelemetryBuffer()


# ──────────────────────────────────────────────────────────────
# Entry point for telemetry recording
# (used as drop-in for backend.modules.codex.codex_trace.record_event)
# ──────────────────────────────────────────────────────────────
def record_event(event_type: str, **fields):
    """Intercept and store telemetry for visualization."""
    payload = {
        "timestamp": time.time(),
        "event_type": event_type,
        **fields,
    }
    telemetry_buffer.append(payload)


# ──────────────────────────────────────────────────────────────
# CodexRender Visualization Engine
# ──────────────────────────────────────────────────────────────
class CodexRender:
    """
    Visual analytics engine for λ–ψ–E telemetry streams.
    Provides live plotting, historical export, and file output.
    """

    def __init__(self):
        self.history = defaultdict(list)

    # ──────────────────────────────────────────────────────────────
    def ingest(self, events: Optional[List[Dict[str, Any]]] = None):
        """Process buffered events and update internal history."""
        if events is None:
            events = telemetry_buffer.snapshot()

        for ev in events:
            etype = ev.get("event_type")
            ts = ev.get("timestamp", time.time())
            if etype in ("law_weight_update", "resonant_weight_update"):
                self.history["lambda"].append((ts, ev.get("new_weight", 0.0)))
            elif etype == "wave_energy":
                self.history["energy"].append((ts, ev.get("value", 0.0)))
            elif etype == "coherence_index":
                self.history["coherence"].append((ts, ev.get("value", 0.0)))

    # ──────────────────────────────────────────────────────────────
    def plot(self, show: bool = True, save_path: Optional[str] = None):
        """
        Render λ(t), E(t), and C(t) trajectories.
        Parameters
        ----------
        show : bool
            Whether to display the figure interactively.
        save_path : str | None
            If provided, saves the figure to this path.
        """
        if not self.history:
            print("No telemetry data available.")
            return

        fig, axes = plt.subplots(3, 1, figsize=(8, 8))
        plt.subplots_adjust(hspace=0.4)

        def plot_series(ax, key, label, color):
            if key not in self.history or not self.history[key]:
                return
            ts, vals = zip(*self.history[key])
            t0 = ts[0]
            t = np.array(ts) - t0
            ax.plot(t, vals, color=color, label=label)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel(label)
            ax.legend()
            ax.grid(True, alpha=0.3)

        plot_series(axes[0], "lambda", "λ(t)", "tab:blue")
        plot_series(axes[1], "energy", "E(t)", "tab:green")
        plot_series(axes[2], "coherence", "C(t)", "tab:orange")

        fig.suptitle("Tessaris Symatics Telemetry — λ/ψ/E Evolution", fontsize=12)
        plt.tight_layout()

        # Handle save/show modes
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=200)
            print(f"✅ Saved visualization to {save_path}")

        if show:
            plt.show()
        else:
            plt.close(fig)

    # ──────────────────────────────────────────────────────────────
    def export_json(self) -> Dict[str, Any]:
        """Return history as serializable dict for Codex UI."""
        return {k: [{"t": t, "v": v} for t, v in series] for k, series in self.history.items()}

    # ──────────────────────────────────────────────────────────────
    # Live Streaming Visualization
    # ──────────────────────────────────────────────────────────────
    def live_mode(self, interval: float = 0.5, duration: Optional[float] = None):
        """
        Display λ(t), E(t), and C(t) curves in real time as telemetry arrives.

        Parameters
        ----------
        interval : float
            Refresh period in seconds between plot updates.
        duration : float | None
            Total duration of live run in seconds (None = infinite until closed).
        """
        import matplotlib.animation as animation

        if not hasattr(self, "fig"):
            self.fig, self.axes = plt.subplots(3, 1, figsize=(8, 8))
            self.lines = [
                self.axes[i].plot([], [], color=c, label=l)[0]
                for i, (c, l) in enumerate(
                    [("tab:blue", "λ(t)"), ("tab:green", "E(t)"), ("tab:orange", "C(t)")]
                )
            ]
            for i, lbl in enumerate(["λ(t)", "E(t)", "C(t)"]):
                self.axes[i].set_xlim(0, 10)
                self.axes[i].set_ylim(0, 1.2)
                self.axes[i].set_ylabel(lbl)
                self.axes[i].legend()
                self.axes[i].grid(True, alpha=0.3)
            self.fig.suptitle("Tessaris Δ-Telemetry — Live λ/ψ/E Stream", fontsize=12)

        start_time = time.time()

        def update(_):
            self.ingest()
            for i, key in enumerate(["lambda", "energy", "coherence"]):
                if key in self.history and self.history[key]:
                    t, v = zip(*self.history[key])
                    t = np.array(t) - t[0]
                    self.lines[i].set_data(t, v)
                    xmax = max(t) if max(t) > 5 else 5
                    self.axes[i].set_xlim(0, xmax)
            if duration and (time.time() - start_time) > duration:
                plt.close(self.fig)
            return self.lines

        ani = animation.FuncAnimation(
            self.fig, update, interval=interval * 1000, blit=False
        )
        plt.show()


# ──────────────────────────────────────────────────────────────
# Example standalone diagnostic mode
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Mock some telemetry
    for i in range(100):
        record_event("law_weight_update", new_weight=1.0 + 0.02 * np.sin(i / 10))
        record_event("wave_energy", value=1.0 - 0.005 * i)
        record_event("coherence_index", value=np.exp(-0.01 * i))
        time.sleep(0.01)

    renderer = CodexRender()
    renderer.ingest()
    renderer.plot(show=False, save_path="docs/figures/demo_lambda_psi_energy.png")