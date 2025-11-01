#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N15 - Active Rephasing with Thermal Compensation
Tests whether introducing a Boltzmann-synced thermal phase correction
can recover stability across cycles and close the energy-information loop.
"""

import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# === Physical constants & parameters ===
ħ = 1e-3
G = 1e-5
Λ0 = 1e-6
α0 = 0.5
β = 0.2
kB = 8.617333262e-5  # Boltzmann constant in eV/K

# Thermodynamic values from N8 (approx)
T_eff = 3.645e18      # effective temperature (K)
ΔE = 1.21e14 * 1.602e-19  # convert eV to Joules (~1.94e-5 J)
cycles = 4
rephase_gain = 0.35

# === Time and signal setup ===
t = np.linspace(0, 10, 2000)
ψ1 = np.exp(-t/10) * np.cos(t)  # base input signal

# === Initialize arrays ===
fidelities = []
phase_errors = []
temps = []
ψ_prev = ψ1.copy()

# === Simulation Loop ===
for n in range(cycles):
    # temperature coupling term (Boltzmann)
    T_cycle = T_eff * (1 + 0.01 * np.sin(n))  # slight modulation
    temps.append(T_cycle)

    thermal_factor = np.exp(-ΔE / (kB * T_cycle))
    φ_corr = rephase_gain * thermal_factor

    # generate phase-corrected signal
    ψ_next = ψ_prev * np.exp(-1j * (β * t - φ_corr * np.sin(t)))

    # compute fidelity
    F = np.abs(np.vdot(ψ_prev, ψ_next)) / (np.linalg.norm(ψ_prev) * np.linalg.norm(ψ_next))
    fidelities.append(F)

    # phase error estimation
    Δφ = np.angle(np.vdot(ψ_prev, ψ_next))
    phase_errors.append(Δφ)

    ψ_prev = ψ_next.copy()

mean_fidelity = np.mean(fidelities)
mean_phase_error = np.mean(phase_errors)

# === Classification ===
if mean_fidelity > 0.9 and abs(mean_phase_error) < 0.2:
    classification = "✅ Stable (Thermal Equilibrium)"
elif mean_fidelity > 0.6:
    classification = "⚠️ Partially stabilized"
else:
    classification = "❌ Unstable (Thermal drift)"

# === Plot 1: Fidelity vs cycle ===
plt.figure(figsize=(8,5))
plt.plot(range(1, cycles+1), fidelities, 'bo-', label="Rephased Fidelity")
plt.axhline(0.9, color='r', linestyle='--', label='90% stability threshold')
plt.xlabel("Cycle #")
plt.ylabel("Fidelity |⟨ψn|ψn+1⟩|")
plt.title("N15 - Thermal Rephasing Stability Across Cycles")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_N15_FidelityCycles.png")

# === Plot 2: Phase drift vs temperature ===
plt.figure(figsize=(8,5))
plt.plot(range(1, cycles+1), phase_errors, 'o-', color='orange', label="Phase error (radians)")
plt.xlabel("Cycle #")
plt.ylabel("Phase Error (Δφ)")
plt.title("N15 - Phase Drift vs Thermal Compensation")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_N15_PhaseDrift.png")

print("=== N15 - Thermal Rephasing & Feedback Equilibrium Test ===")
print(f"ħ={ħ:.3e}, G={G:.1e}, Λ0={Λ0:.1e}, α0={α0:.3f}, β={β:.2f}, T_eff={T_eff:.3e} K")
print(f"Mean fidelity={mean_fidelity:.3f}, Mean Δφ={mean_phase_error:.3f} rad")
print(f"Classification: {classification}")
print("✅ Plots saved: PAEV_N15_FidelityCycles.png, PAEV_N15_PhaseDrift.png")

# === Save summary ===
summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α0": α0,
    "β": β,
    "T_eff": T_eff,
    "ΔE_J": ΔE,
    "rephase_gain": rephase_gain,
    "cycles": cycles,
    "fidelities": fidelities,
    "phase_errors": phase_errors,
    "mean_fidelity": mean_fidelity,
    "mean_phase_error": mean_phase_error,
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

summary_path = "backend/modules/knowledge/N15_thermal_rephase_summary.json"
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"📄 Summary: {summary_path}")
print("----------------------------------------------------------")