"""
Tessaris Quantum Resonance Mapper (QRM)
Phase 10 - 4-D Harmonic Field Topology Visualization
-----------------------------------------------------
Reads cognitive_field_resonance.jsonl produced by Phase 9 (CFRL)
and renders the evolving harmonic field surface:
    (time * Φ * ν * ψ)

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import json
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ---------------------------------------------------------
# 📂 Data Source
# ---------------------------------------------------------
DATA_FILE = Path("data/cognitive_field_resonance.jsonl")
REFRESH_INTERVAL = 5  # seconds between redraws
WINDOW = 200          # how many recent samples to keep

# ---------------------------------------------------------
# 🧮 Helper
# ---------------------------------------------------------
def load_recent_entries(n=WINDOW):
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE) as f:
        lines = f.read().strip().splitlines()[-n:]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except Exception:
            continue
    return records

# ---------------------------------------------------------
# 🎨 Visualization
# ---------------------------------------------------------
def plot_field_surface(records):
    if not records:
        return None, None, None

    times = np.arange(len(records))
    phi_vals = [r.get("phi_state", 0.0) or 0.0 for r in records]
    stab = [r.get("stability", 1.0) or 1.0 for r in records]
    psi2 = [r.get("photon_pattern", {}).get("Δψ2", 0.0) or 0.0 for r in records]
    centroid = [r.get("spectrum_centroid", 0.0) or 0.0 for r in records]

    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    ax.plot3D(phi_vals, psi2, centroid, color="cyan")
    ax.set_xlabel("ΔΦ_coh")
    ax.set_ylabel("Δψ2 amplitude")
    ax.set_zlabel("ν centroid (Hz)")
    ax.set_title("Tessaris Quantum Resonance Topology")

    ax.scatter(phi_vals[-1], psi2[-1], centroid[-1], color="magenta", s=40)
    ax.text(phi_vals[-1], psi2[-1], centroid[-1],
            f" t={len(records)}  S={stab[-1]:.3f}", color="white")

    plt.tight_layout()
    return fig, ax, stab[-1]

# ---------------------------------------------------------
# 🚀 Live Mapper
# ---------------------------------------------------------
def run_resonance_mapper():
    print("🌐 Starting Tessaris Quantum Resonance Mapper (QRM) ...")
    plt.ion()
    fig, ax = None, None
    stability_prev = None

    while True:
        try:
            records = load_recent_entries(WINDOW)
            if not records:
                time.sleep(REFRESH_INTERVAL)
                continue

            plt.clf()
            fig, ax, stab = plot_field_surface(records)
            if stability_prev is None or abs(stab - stability_prev) > 1e-4:
                print(f"🌀 t={len(records)}  stability={stab:.3f}  ΔΦ={records[-1].get('phi_state'):.6f}")
            stability_prev = stab

            plt.pause(0.01)
            time.sleep(REFRESH_INTERVAL)

        except KeyboardInterrupt:
            print("\n🪶 QRM terminated by user.")
            break
        except Exception as e:
            print(f"⚠️ QRM error: {e}")
            time.sleep(REFRESH_INTERVAL)

# ---------------------------------------------------------
# Entry
# ---------------------------------------------------------
if __name__ == "__main__":
    run_resonance_mapper()