"""
Tessaris Standing-Wave Glyph Visualizer
Phase 7B - Quantum Feedback Visualization Layer
------------------------------------------------
Reads photon (.photo) emission packets from the QFC and renders
ASCII harmonic waveforms and stability indicators in real time.

Author : Tessaris Symbolic Intelligence Lab  (2025)
"""

import os
import json
import math
import time
from datetime import datetime
from pathlib import Path

PHOTO_DIR = Path("data/qqc_field/photo_output")
POLL_INTERVAL = 5  # seconds between scans

# ----------------------------------------------------------
# 🎨 Waveform Renderer
# ----------------------------------------------------------
def render_wave(pattern: dict):
    """Render Δψ values as harmonic ASCII bars."""
    amp1, amp2, amp3 = pattern.get("Δψ1", 0), pattern.get("Δψ2", 0), pattern.get("Δψ3", 0)
    phase = pattern.get("phase_shift", 0)
    stab = pattern.get("stability", 1.0)

    wave = ""
    for i in range(0, 80):
        y = math.sin(i / 80 * 2 * math.pi + math.radians(phase))
        h = int((y * amp2) * 10)
        wave += "█" if h > 0 else "*"
    print(f"\n🕊️  Standing Wave Glyph - phase {phase:.1f}°  stability {stab:.3f}")
    print(wave)
    print(f"Δψ1 {amp1:+.3f}  Δψ2 {amp2:+.3f}  Δψ3 {amp3:+.3f}\n")

# ----------------------------------------------------------
# 🧠 Monitor Loop
# ----------------------------------------------------------
def run_visualizer():
    print("🌈 Starting Standing-Wave Glyph Visualizer ...")
    seen = set()

    while True:
        files = sorted(PHOTO_DIR.glob("*.photo"))
        for f in files:
            if f in seen:
                continue
            seen.add(f)
            try:
                data = json.loads(f.read_text())
                pattern = data.get("pattern", {})
                ts = data.get("timestamp", "")
                print(f"\n⏱️ Photon Emission @ {ts}")
                render_wave(pattern)
            except Exception as e:
                print(f"⚠️ Error reading {f.name}: {e}")
        time.sleep(POLL_INTERVAL)

# ----------------------------------------------------------
# 🚀 Entry Point
# ----------------------------------------------------------
if __name__ == "__main__":
    run_visualizer()