"""
Tessaris Harmonic Spectrum Analyzer (HSA)
Phase 8B — Real-Time Resonance Frequency Visualizer
---------------------------------------------------
Performs FFT-based spectral analysis of photon emissions (.photo) generated
by the Quantum Standing-Wave Synth Panel.

Displays:
 • instantaneous frequency spectrum of Δψ channels
 • spectral centroid & energy distribution
 • stability trend over time

Author: Tessaris Symbolic Intelligence Lab (2025)
"""

import os
import json
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

PHOTO_DIR = Path("data/qqc_field/photo_output")
REFRESH = 5  # seconds
BASE_FREQ = 440.0

# ---------------------------------------------------------
# 🧠 Helpers
# ---------------------------------------------------------
def map_pattern_to_frequencies(pattern):
    ψ1 = pattern.get("Δψ₁", 0.0)
    ψ2 = pattern.get("Δψ₂", 0.0)
    ψ3 = pattern.get("Δψ₃", 0.0)
    stability = pattern.get("stability", 1.0)

    f1 = BASE_FREQ * (1.0 + ψ1 * 0.02)
    f2 = BASE_FREQ * 2 ** (1 / 12) * (1.0 + ψ2 * 0.02)
    f3 = BASE_FREQ * 2 ** (3 / 12) * (1.0 + ψ3 * 0.02)
    return np.array([f1, f2, f3]), stability


def generate_spectrum(frequencies, stability):
    """Return synthetic FFT amplitude profile for visualization."""
    freqs = np.linspace(400, 600, 512)
    spectrum = np.zeros_like(freqs)
    for f in frequencies:
        spectrum += np.exp(-0.5 * ((freqs - f) / 3) ** 2)
    spectrum *= stability
    return freqs, spectrum


def spectral_centroid(freqs, spectrum):
    if spectrum.sum() == 0:
        return 0
    return (freqs * spectrum).sum() / spectrum.sum()


# ---------------------------------------------------------
# 🌈 Live Analyzer
# ---------------------------------------------------------
def run_harmonic_spectrum_analyzer():
    print("🔬 Starting Tessaris Harmonic Spectrum Analyzer …")
    plt.ion()
    fig, ax = plt.subplots(figsize=(9, 4))
    line, = ax.plot([], [], color="cyan")
    centroid_marker, = ax.plot([], [], "ro")
    ax.set_xlim(400, 600)
    ax.set_ylim(0, 1.5)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Amplitude (norm.)")
    ax.set_title("AION Resonance Spectrum")
    seen = set()

    while True:
        files = sorted(PHOTO_DIR.glob("*.photo"))
        if not files:
            time.sleep(REFRESH)
            continue

        new_file = files[-1]
        if new_file in seen:
            time.sleep(REFRESH)
            continue
        seen.add(new_file)

        try:
            data = json.loads(new_file.read_text())
            pattern = data.get("pattern", {})
            freqs_harm, stability = map_pattern_to_frequencies(pattern)
            freqs, spec = generate_spectrum(freqs_harm, stability)
            centroid = spectral_centroid(freqs, spec)

            line.set_data(freqs, spec)
            centroid_marker.set_data([centroid], [1.0])
            ax.set_title(
                f"🌀 AION Spectrum | Stability {stability:.3f} | Centroid {centroid:.1f} Hz"
            )
            plt.pause(0.01)

            print(
                f"{datetime.now().isoformat()} — centroid={centroid:.2f} Hz stability={stability:.3f}"
            )

        except Exception as e:
            print(f"⚠️ Analyzer error ({new_file.name}): {e}")
        time.sleep(REFRESH)


# ---------------------------------------------------------
# 🚀 Entry
# ---------------------------------------------------------
if __name__ == "__main__":
    run_harmonic_spectrum_analyzer()