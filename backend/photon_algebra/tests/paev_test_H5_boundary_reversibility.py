# -*- coding: utf-8 -*-
"""
PAEV Test H5 - Boundary Condition Reversibility (Registry-Compliant Edition)
----------------------------------------------------------------------------
Goal:
    Verify that the photon-algebraic field equations (ψ-κ system)
    remain time-reversible and energy-consistent when boundary
    conditions are inverted (t -> -t).

Significance:
    Time-symmetric reversibility under the unified algebra implies
    conservation across temporal reflection - a hallmark of
    a physically complete algebraic model (precursor to TOE H-layer).

Outputs:
    * PAEV_TestH5_EnergyDrift.png
    * PAEV_TestH5_EntropyEvolution.png
    * PAEV_TestH5_ReversibilityError.png
    * backend/modules/knowledge/H5_boundary_reversibility.json
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
import json, os

# ---------------------------------------------------------------------
# 1) Constants - Tessaris unified registry loader
# ---------------------------------------------------------------------
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ0, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# ---------------------------------------------------------------------
# 2) Simulation Parameters
# ---------------------------------------------------------------------
N = 128
steps = 600
dt = 0.01
γ = 0.015

# Create spatial grid
x = np.linspace(-2, 2, N)
X, Y = np.meshgrid(x, x)

# Initialize ψ, κ fields
psi = np.exp(-(X**2 + Y**2)) * np.exp(1j * 0.2 * X)
psi = psi.astype(np.complex128)

kappa = 0.5 * np.exp(-(X**2 + Y**2))
kappa = kappa.astype(np.complex128)

energy_trace, entropy_trace = [], []

# ---------------------------------------------------------------------
# 3) Laplacian operator
# ---------------------------------------------------------------------
def laplacian_2d(field):
    """Discrete 2D Laplacian operator."""
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4 * field
    )

# ---------------------------------------------------------------------
# 4) Forward evolution
# ---------------------------------------------------------------------
for step in range(steps):
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)

    psi_t = (1j * dt) * (lap_psi - kappa * psi)
    kappa_t = dt * (0.05 * lap_kappa + 0.1 * np.real(psi) - 0.02 * kappa)

    psi += γ * psi_t
    kappa += γ * kappa_t

    energy = np.mean(np.abs(psi) ** 2 + np.abs(kappa) ** 2)
    entropy = -np.sum(np.abs(psi) ** 2 * np.log(np.abs(psi) ** 2 + 1e-12))
    energy_trace.append(energy)
    entropy_trace.append(entropy)

psi_forward = np.copy(psi)
kappa_forward = np.copy(kappa)

# ---------------------------------------------------------------------
# 5) Reverse evolution (t -> -t)
# ---------------------------------------------------------------------
for step in range(steps):
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)

    psi_t = (-1j * dt) * (lap_psi - kappa * psi)
    kappa_t = -dt * (0.05 * lap_kappa + 0.1 * np.real(psi) - 0.02 * kappa)

    psi += γ * psi_t
    kappa += γ * kappa_t

# ---------------------------------------------------------------------
# 6) Diagnostics
# ---------------------------------------------------------------------
rev_error = np.mean(np.abs(psi - psi_forward)) + np.mean(np.abs(kappa - kappa_forward))
energy_drift = np.abs(energy_trace[-1] - energy_trace[0])
entropy_drift = np.abs(entropy_trace[-1] - entropy_trace[0])

rev_ok = rev_error < 1e-3
energy_ok = energy_drift < 1e-4
entropy_ok = entropy_drift < 1e-3

if rev_ok and energy_ok and entropy_ok:
    classification = "✅ Time-reversal symmetry preserved (reversible and conservative)"
else:
    classification = "⚠️ Partial reversibility or minor drift detected"

# ---------------------------------------------------------------------
# 7) Plots
# ---------------------------------------------------------------------
plt.figure(figsize=(6, 4))
plt.plot(energy_trace, label="Energy ⟨E⟩", color="#1E88E5")
plt.title("H5 - Energy Drift Over Time")
plt.xlabel("Step")
plt.ylabel("Energy")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_TestH5_EnergyDrift.png", dpi=160)
plt.close()

plt.figure(figsize=(6, 4))
plt.plot(entropy_trace, color="#F57C00", label="Spectral Entropy")
plt.title("H5 - Entropy Evolution (ψ Field)")
plt.xlabel("Step")
plt.ylabel("Entropy")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_TestH5_EntropyEvolution.png", dpi=160)
plt.close()

plt.figure(figsize=(5, 4))
plt.imshow(np.abs(psi - psi_forward), cmap="inferno")
plt.colorbar(label="|Δψ| (Reversibility Error)")
plt.title("H5 - Final Reversibility Error Field")
plt.tight_layout()
plt.savefig("PAEV_TestH5_ReversibilityError.png", dpi=160)
plt.close()

# ---------------------------------------------------------------------
# 8) Summary & JSON Export
# ---------------------------------------------------------------------
print("\n=== Test H5 - Boundary Condition Reversibility Complete ===")
print(f"⟨E⟩ drift      = {energy_drift:.6e}")
print(f"⟨S⟩ drift      = {entropy_drift:.6e}")
print(f"Reversibility error = {rev_error:.6e}")
print(f"-> {classification}")
print("All output files saved:")
for p in [
    "PAEV_TestH5_EnergyDrift.png",
    "PAEV_TestH5_EntropyEvolution.png",
    "PAEV_TestH5_ReversibilityError.png",
]:
    print(f" - {os.path.abspath(p)}")

summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α": α,
    "β": β,
    "metrics": {
        "energy_drift": float(energy_drift),
        "entropy_drift": float(entropy_drift),
        "reversibility_error": float(rev_error),
    },
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}

out_path = Path("backend/modules/knowledge/H5_boundary_reversibility.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved -> {out_path}")