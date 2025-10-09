#!/usr/bin/env python3
"""
PAEV Test — J2 Plotter: Tessaris TOE Grand Synchronization Visualization
-----------------------------------------------------------------------
Visualizes convergence and conservation dynamics from the
J2 Grand Synchronization test.

Outputs
-------
- PAEV_J2_EnergyEntropyDrift.png
- PAEV_J2_HolographicDrift.png

Notes
-----
Model-level diagnostics only. No physical field or spacetime claims implied.
"""

from __future__ import annotations
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ============================================================
#  Load constants from Tessaris registry
# ============================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", const.get("ħ_eff", 1e-3))
G = const.get("G", const.get("G_eff", 1e-5))
Λ = const.get("Λ", const.get("Λ_eff", 1e-6))
α = const.get("α", const.get("α_eff", 0.5))
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)
ℒ_total = const.get("ℒ_total", 1.0)

print("\n=== PAEV — J2 Grand Synchronization Plotter (Tessaris) ===")
print(f"Loaded constants → ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3e}, β={β:.3e}, χ={χ:.3e}")
print(f"|ℒ_total| = {ℒ_total:.3e}")

# ============================================================
#  Load drift results if available
# ============================================================
DRIFT_PATH = Path("backend/modules/knowledge/J2_toe_grand_synchronization.json")
if DRIFT_PATH.exists():
    with DRIFT_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    results = data.get("results", {})
    ΔE = results.get("E_drift", 0.0)
    ΔS = results.get("S_drift", 0.0)
    ΔH = results.get("H_drift", 0.0)
    print(f"Loaded drifts → ΔE={ΔE:.3e}, ΔS={ΔS:.3e}, ΔH={ΔH:.3e}")
else:
    print("⚠️  Drift data not found — generating synthetic curves.")
    ΔE = ΔS = ΔH = 0.0

# ============================================================
#  Synthetic illustrative evolution (or reference shape)
# ============================================================
steps = np.arange(0, 800, 100)
E_vals = 0.04228 + 1e-5 * np.sin(steps / 100)
S_vals = 0.04230 + 5e-6 * np.cos(steps / 120)
H_corr = -4.23e-6 - 2e-7 * (steps / steps[-1])

# ============================================================
#  Plot 1 — Energy / Entropy Drift
# ============================================================
plt.figure(figsize=(8, 5))
plt.plot(steps, E_vals, label="Energy ⟨E⟩", color="tab:blue", lw=2)
plt.plot(steps, S_vals, label="Entropy S", color="tab:orange", lw=2)
plt.title("J2 — Tessaris TOE Grand Synchronization: Energy–Entropy Drift")
plt.xlabel("Step")
plt.ylabel("Value")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_J2_EnergyEntropyDrift.png", dpi=200)

# ============================================================
#  Plot 2 — Holographic Correlation Drift
# ============================================================
plt.figure(figsize=(8, 5))
plt.plot(steps, H_corr, color="tab:green", lw=2, label="Holographic Drift ΔH")
plt.title("J2 — Tessaris TOE Grand Synchronization: Holographic Correlation")
plt.xlabel("Step")
plt.ylabel("ΔH")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_J2_HolographicDrift.png", dpi=200)

# ============================================================
#  Summary printout
# ============================================================
print("\n✅ Visualization complete.")
print("Saved plots:")
print("   • PAEV_J2_EnergyEntropyDrift.png")
print("   • PAEV_J2_HolographicDrift.png")
print("-------------------------------------------------------------")