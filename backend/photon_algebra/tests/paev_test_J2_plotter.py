"""
PAEV Test — J2 Plotter: TOE Grand Synchronization Visualization
---------------------------------------------------------------
This script visualizes the convergence and conservation dynamics
of the TOE J2 synchronization test.
"""

from __future__ import annotations
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------
# Load constants from the TOE export (constants_v1.1.json)
# ---------------------------------------------------------------------
CONST_PATH = Path("backend/modules/knowledge/constants_v1.1.json")
if not CONST_PATH.exists():
    raise FileNotFoundError(f"❌ Missing constants file at {CONST_PATH}")

with open(CONST_PATH, "r", encoding="utf-8") as f:
    constants = json.load(f)

ħ = constants["ħ_eff"]
G = constants["G_eff"]
Λ = constants["Λ_eff"]
α = constants["α_eff"]
drifts = constants.get("drifts", {})
ΔE, ΔS, ΔH = drifts.get("ΔE", 0), drifts.get("ΔS", 0), drifts.get("ΔH", 0)

# ---------------------------------------------------------------------
# Generate synthetic temporal evolution (illustrative)
# ---------------------------------------------------------------------
steps = np.arange(0, 800, 100)
E_vals = 0.04228 + 1e-5 * np.sin(steps / 100)
S_vals = 0.0423 + 5e-6 * np.cos(steps / 120)
H_corr = -4.23e-6 - 2e-7 * (steps / steps[-1])

# ---------------------------------------------------------------------
# Plot 1 — Energy / Entropy Drift
# ---------------------------------------------------------------------
plt.figure(figsize=(8, 5))
plt.plot(steps, E_vals, label="Energy ⟨E⟩", color="tab:blue")
plt.plot(steps, S_vals, label="Entropy S", color="tab:orange")
plt.title("J2 — TOE Grand Synchronization: Energy–Entropy Drift")
plt.xlabel("Step")
plt.ylabel("Value")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_J2_EnergyEntropyDrift.png", dpi=200)

# ---------------------------------------------------------------------
# Plot 2 — Holographic Correlation Drift
# ---------------------------------------------------------------------
plt.figure(figsize=(8, 5))
plt.plot(steps, H_corr, color="tab:green", label="Holographic Drift ΔH")
plt.title("J2 — TOE Grand Synchronization: Holographic Correlation")
plt.xlabel("Step")
plt.ylabel("ΔH")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_J2_HolographicDrift.png", dpi=200)

# ---------------------------------------------------------------------
# Summary printout
# ---------------------------------------------------------------------
print("\n=== J2 Plotter — TOE Grand Synchronization Visualization ===")
print(f"Loaded constants from: {CONST_PATH}")
print(f"ħ_eff = {ħ:.3e},  G_eff = {G:.3e},  Λ_eff = {Λ:.3e},  α_eff = {α:.3f}")
print(f"Drifts: ΔE={ΔE:.3e}, ΔS={ΔS:.3e}, ΔH={ΔH:.3e}")
print("✅ Plots saved:")
print("   - PAEV_J2_EnergyEntropyDrift.png")
print("   - PAEV_J2_HolographicDrift.png")
print("-------------------------------------------------------------")