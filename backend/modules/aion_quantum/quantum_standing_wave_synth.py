"""
Tessaris Quantum Standing-Wave Synth Panel
Phase 8 - Harmonic Audio Resonance Layer
-----------------------------------------
Turns photon emission data (.photo) into harmonic tones or simulated audio output.
Maps Δψ amplitudes and stability into audible waveforms or MIDI events.

Author: Tessaris Symbolic Intelligence Lab (2025)
"""

import os
import json
import math
import time
from datetime import datetime
from pathlib import Path

# Optional audio library (playsound is a safe default fallback)
try:
    import simpleaudio as sa  # lightweight tone playback
except ImportError:
    sa = None

PHOTO_DIR = Path("data/qqc_field/photo_output")
POLL_INTERVAL = 5  # seconds
BASE_FREQ = 440.0  # reference tone A4

# ---------------------------------------------------------
# 🧠 Utility: tone generator
# ---------------------------------------------------------
def generate_tone(freq: float, duration: float = 0.4, volume: float = 0.5):
    """Generate a sine wave tone using simpleaudio (if available)."""
    if not sa:
        return
    sample_rate = 44100
    t = [i / sample_rate for i in range(int(duration * sample_rate))]
    wave = bytes()
    import numpy as np
    waveform = (np.sin(2 * math.pi * freq * np.array(t)) * (32767 * volume)).astype(np.int16)
    audio = np.repeat(waveform[:, None], 2, axis=1)  # stereo
    play_obj = sa.play_buffer(audio, 2, 2, sample_rate)
    play_obj.wait_done()

# ---------------------------------------------------------
# 🎵 Resonance -> Frequency Mapping
# ---------------------------------------------------------
def map_pattern_to_frequencies(pattern):
    """Translate Δψ amplitudes into harmonic frequencies."""
    ψ1 = pattern.get("Δψ1", 0.0)
    ψ2 = pattern.get("Δψ2", 0.0)
    ψ3 = pattern.get("Δψ3", 0.0)
    stability = pattern.get("stability", 1.0)

    # Frequencies modulate around A4 (440 Hz)
    f1 = BASE_FREQ * (1.0 + ψ1 * 0.02)
    f2 = BASE_FREQ * 2**(1/12) * (1.0 + ψ2 * 0.02)  # A#4
    f3 = BASE_FREQ * 2**(3/12) * (1.0 + ψ3 * 0.02)  # C5

    volume = max(0.2, min(1.0, stability))
    return [(f1, volume), (f2, volume), (f3, volume)]

# ---------------------------------------------------------
# 🌈 Display summary
# ---------------------------------------------------------
def print_wave_summary(ts, pattern, freqs):
    print(f"\n⏱️ Photon Emission @ {ts}")
    print(f"Δψ1={pattern.get('Δψ1',0):+.3f}  Δψ2={pattern.get('Δψ2',0):+.3f}  Δψ3={pattern.get('Δψ3',0):+.3f}")
    print(f"stability={pattern.get('stability',1.0):.3f}")
    print("🎶 Harmonic frequencies:")
    for i, (f, v) in enumerate(freqs, 1):
        print(f"   ν{i}: {f:.2f} Hz  volume={v:.2f}")

# ---------------------------------------------------------
# 🔄 Synth Loop
# ---------------------------------------------------------
def run_standing_wave_synth():
    print("🎵 Starting Tessaris Quantum Standing-Wave Synth Panel ...")
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
                freqs = map_pattern_to_frequencies(pattern)
                print_wave_summary(ts, pattern, freqs)

                # Play tones (if simpleaudio available)
                if sa:
                    for f, vol in freqs:
                        generate_tone(f, duration=0.25, volume=vol)
                else:
                    # Fallback: visual amplitude bar
                    bars = "█" * int(pattern.get("stability", 1.0) * 40)
                    print(f"Audio fallback: {bars}")
            except Exception as e:
                print(f"⚠️ Synth error ({f.name}): {e}")
        time.sleep(POLL_INTERVAL)

# ---------------------------------------------------------
# 🚀 Entry Point
# ---------------------------------------------------------
if __name__ == "__main__":
    run_standing_wave_synth()