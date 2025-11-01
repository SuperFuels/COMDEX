"""
Tessaris * QQC v0.5 - Symatics Lightwave Engine
Wave Modulation Telemetry Plotter
──────────────────────────────────────────────
Visualizes amplitude, phase, frequency, and coherence
evolution across ticks for each Symatics operator (⊕, ↔, μ, ⟲, π).

Usage:
    PYTHONPATH=. python backend/scripts/plot_wave_modulation.py
"""

import time
import math
import matplotlib.pyplot as plt
from backend.codexcore_virtual.virtual_wave_engine import VirtualWaveEngine
from backend.modules.glyphwave.core.wave_state import WaveState

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
OPERATORS = ["⊕", "↔", "μ", "⟲", "π"]
TICKS_PER_OP = 5

# ──────────────────────────────────────────────
# Run test sequence
# ──────────────────────────────────────────────
def run_modulation_sequence():
    engine = VirtualWaveEngine(container_id="sle.plot_test")
    wave = WaveState()
    wave.id = "plot_wave"
    engine.attach_wave(wave)

    telemetry = {op: {"amp": [], "phase": [], "freq": [], "coh": []} for op in OPERATORS}

    for opcode in OPERATORS:
        engine.load_wave_program([{"opcode": opcode}])
        for _ in range(TICKS_PER_OP):
            engine._apply_symatics_modulation(wave, opcode)
            wave.evolve()
            telemetry[opcode]["amp"].append(wave.amplitude)
            telemetry[opcode]["phase"].append(wave.phase)
            telemetry[opcode]["freq"].append(wave.frequency)
            telemetry[opcode]["coh"].append(wave.coherence)
            time.sleep(0.05)

    return telemetry

# ──────────────────────────────────────────────
# Plot results
# ──────────────────────────────────────────────
def plot_modulation(telemetry):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Tessaris QQC v0.5 - Symatics Lightwave Modulation Evolution", fontsize=14, fontweight="bold")

    params = ["amp", "phase", "freq", "coh"]
    titles = ["Amplitude", "Phase (radians)", "Frequency", "Coherence"]
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]

    for ax, param, title, color in zip(axes.flat, params, titles, colors):
        for opcode in OPERATORS:
            ax.plot(range(1, len(telemetry[opcode][param]) + 1),
                    telemetry[opcode][param],
                    marker="o", label=opcode)
        ax.set_title(title)
        ax.set_xlabel("Tick")
        ax.set_ylabel(param.capitalize())
        ax.grid(True, alpha=0.3)
        ax.legend(title="Operator", loc="best", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig("outputs/wave_modulation_plot.png", dpi=200)
    plt.show()

# ──────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📡 Running Symatics Lightwave Telemetry Plotter...\n")
    telemetry = run_modulation_sequence()
    plot_modulation(telemetry)
    print("\n✅ Plot generated: outputs/wave_modulation_plot.png\n")