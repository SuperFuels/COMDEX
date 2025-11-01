"""
Tessaris Colorized Interference Visualizer
Phase 7C - Harmonic Field Coherence Display
-------------------------------------------
Reads .photo emissions from the Quantum Feedback Coupler (QFC)
and renders colored harmonic waveforms with interference overlays.

Blue -> stable field
Yellow -> modulated field
Red -> unstable / decohering field
Author : Tessaris Symbolic Intelligence Lab (2025)
"""

import os
import json
import math
import time
import colorsys
from datetime import datetime
from pathlib import Path

# Terminal color codes (ANSI)
RESET = "\033[0m"
def rgb(r,g,b): return f"\033[38;2;{r};{g};{b}m"

# Data directory for photon outputs
PHOTO_DIR = Path("data/qqc_field/photo_output")
POLL_INTERVAL = 5  # seconds

# ---------------------------------------------------------
# 🎨 Color mapping
# ---------------------------------------------------------
def stability_to_color(stability: float):
    """Map stability (0-1) to RGB gradient."""
    if stability > 0.95:
        return rgb(0, 170, 255)      # Blue: perfectly stable
    elif stability > 0.8:
        return rgb(255, 255, 0)      # Yellow: modulated
    else:
        return rgb(255, 80, 80)      # Red: unstable

# ---------------------------------------------------------
# 🌊 Waveform Rendering
# ---------------------------------------------------------
def render_interference(pattern):
    """Render interference pattern for Δψ2 and Δψ3."""
    amp1 = pattern.get("Δψ1", 0.0)
    amp2 = pattern.get("Δψ2", 0.0)
    amp3 = pattern.get("Δψ3", 0.0)
    phase = pattern.get("phase_shift", 0.0)
    stab = pattern.get("stability", 1.0)

    color = stability_to_color(stab)
    print(f"{color}\n🌀 Resonant Field Snapshot - stability={stab:.3f} phase={phase:.1f}°{RESET}")

    # Generate interference pattern
    bars = ""
    for i in range(80):
        θ = i / 80 * 2 * math.pi
        y = math.sin(θ + math.radians(phase)) * amp2
        y2 = math.sin(θ + math.radians(phase + 45)) * amp3  # shifted interference
        inter = (y + y2) / 2
        h = int(inter * 10)
        bars += "█" if h > 0 else "*"

    print(f"{color}{bars}{RESET}")
    print(f"Δψ1 {amp1:+.3f}  Δψ2 {amp2:+.3f}  Δψ3 {amp3:+.3f}\n")

# ---------------------------------------------------------
# 🧭 Monitor Loop
# ---------------------------------------------------------
def run_colorized_visualizer():
    print("🌌 Starting Tessaris Colorized Interference Visualizer ...")
    seen = set()

    while True:
        files = sorted(PHOTO_DIR.glob("*.photo"))
        for f in files:
            if f in seen:
                continue
            seen.add(f)
            try:
                data = json.loads(f.read_text())
                ts = data.get("timestamp", "")
                pattern = data.get("pattern", {})
                print(f"\n⏱️ Photon emission detected @ {ts}")
                render_interference(pattern)
            except Exception as e:
                print(f"⚠️ Error parsing {f.name}: {e}")
        time.sleep(POLL_INTERVAL)

# ---------------------------------------------------------
# 🚀 Entry Point
# ---------------------------------------------------------
if __name__ == "__main__":
    run_colorized_visualizer()