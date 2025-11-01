#!/usr/bin/env python3
"""
Tessaris Phase 19 - Quantum Resonant Field Visualizer (QRFV)

Aggregates and visualizes multi-source quantum cognition telemetry from Tessaris subsystems.
Displays harmonic coherence, feedback weights, symbolic entropy, and forecast confidence
over time to illustrate self-stabilizing resonance cognition.
"""

import json
import time
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ── Data sources ───────────────────────────────────────────────
RQFS_PATH = Path("data/learning/rqfs_sync.jsonl")
FORECAST_PATH = Path("data/cognition/forecast_stream.jsonl")
ASM_PATH = Path("data/cognition/asm_memory.jsonl")
HCO_PATH = Path("data/learning/harmonic_field.log")  # optional

# ── Settings ──────────────────────────────────────────────────
WINDOW = 200  # recent samples to show
REFRESH = 5.0  # seconds

def load_jsonl(path, limit=WINDOW):
    if not path.exists():
        return []
    with open(path) as f:
        lines = f.readlines()[-limit:]
    data = []
    for l in lines:
        try:
            data.append(json.loads(l))
        except Exception:
            continue
    return data

def extract_time_series(rqfs, forecast, asm):
    times, nu_bias, amp_gain, entropy, conf = [], [], [], [], []
    for entry in rqfs:
        times.append(datetime.fromisoformat(entry["timestamp"]))
        nu_bias.append(entry.get("nu_bias", 0.0))
        amp_gain.append(entry.get("amp_gain", 1.0))
    for i, m in enumerate(asm[-len(times):]):
        entropy.append(m.get("entropy", 0.0))
    for i, f in enumerate(forecast[-len(times):]):
        conf.append(f.get("confidence", 0.0))
    return times, nu_bias, amp_gain, entropy, conf

def live_plot():
    print("🌀 Starting Tessaris Quantum Resonant Field Visualizer (QRFV)...")
    plt.style.use("ggplot")
    fig, ax = plt.subplots(figsize=(10,6))
    plt.title("Tessaris Resonant Field Dynamics")
    plt.xlabel("Time")
    plt.ylabel("Magnitude")

    line_nu, = ax.plot([], [], label="ν_bias", lw=2)
    line_amp, = ax.plot([], [], label="Amplitude Gain", lw=2)
    line_entropy, = ax.plot([], [], label="Symbolic Entropy", lw=1.5)
    line_conf, = ax.plot([], [], label="Forecast Confidence", lw=1.5)

    ax.legend(loc="upper left")
    ax.set_ylim(-2, 6)

    def update(_):
        rqfs = load_jsonl(RQFS_PATH)
        forecast = load_jsonl(FORECAST_PATH)
        asm = load_jsonl(ASM_PATH)
        if not rqfs:
            return line_nu, line_amp, line_entropy, line_conf

        t, nu, amp, ent, conf = extract_time_series(rqfs, forecast, asm)
        line_nu.set_data(t, nu)
        line_amp.set_data(t, amp)
        line_entropy.set_data(t, ent)
        line_conf.set_data(t, conf)
        ax.relim(); ax.autoscale_view()
        return line_nu, line_amp, line_entropy, line_conf

    ani = animation.FuncAnimation(fig, update, interval=REFRESH*1000, blit=False)
    plt.show()

def main():
    live_plot()

if __name__ == "__main__":
    main()