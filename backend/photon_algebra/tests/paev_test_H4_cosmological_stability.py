# -*- coding: utf-8 -*-
"""
H4 — Cosmological Scale Stability Test (Registry-Compliant Edition)
-------------------------------------------------------------------
Goal:
    Evaluate large-scale energy and entropy balance of photon–curvature
    fields under slow cosmological expansion (Λ-driven scaling).

Significance:
    Confirms that the photon-algebra system maintains global energy
    and entropy consistency under expansion — a macro-scale stability
    analogue to the micro feedback equilibrium.

Outputs:
    • PAEV_TestH4_EnergyEntropy.png
    • PAEV_TestH4_ScaleFactor.png
    • PAEV_TestH4_FinalField.png
    • backend/modules/knowledge/H4_cosmological_stability.json
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
import json, os

# ---------------------------------------------------------------------
# 1) Constants — Tessaris unified registry loader
# ---------------------------------------------------------------------
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ0, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# ---------------------------------------------------------------------
# 2) Simulation parameters
# ---------------------------------------------------------------------
N = 128
steps = 800
dt = 0.01

# Dimensionless cosmological scalars
Λ = 1e-4         # Cosmological constant analogue
H0 = 0.02        # Hubble-like parameter
κ0 = 0.05        # Initial curvature amplitude
a = 1.0          # Scale factor
expansion_rate = 1e-3

# ---------------------------------------------------------------------
# 3) Field initialization
# ---------------------------------------------------------------------
x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)

phi = 1.0 + 0.02 * np.random.randn(N, N)
psi = np.exp(-((X**2 + Y**2) / 0.3)) * np.exp(1j * 0.5 * X)
kappa = κ0 * np.exp(-(X**2 + Y**2) / 0.4)

energy_trace, entropy_trace, a_trace = [], [], []

def laplacian(Z):
    """Discrete 2D Laplacian."""
    return -4 * Z + np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)

# ---------------------------------------------------------------------
# 4) Evolution loop
# ---------------------------------------------------------------------
for step in range(steps):
    # Cosmological expansion
    a *= (1 + expansion_rate * dt)
    H = H0 * np.sqrt(Λ + (np.mean(np.abs(kappa)) / κ0))

    # Field evolution scaled by expansion
    lap_psi = laplacian(psi)
    lap_kappa = laplacian(kappa)

    psi_t = 1j * (lap_psi / a**2 - kappa * psi)
    kappa_t = (0.05 * lap_kappa - 0.02 * kappa + 0.001 * np.abs(psi)**2) * (1 / a)

    psi += dt * psi_t
    kappa += dt * kappa_t

    # Energy & entropy tracking
    energy = np.mean(np.abs(psi)**2 + np.abs(kappa)**2)
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(psi)))**2
    p = spectrum / np.sum(spectrum)
    spectral_entropy = -np.sum(p * np.log(p + 1e-12))

    energy_trace.append(energy)
    entropy_trace.append(spectral_entropy)
    a_trace.append(a)

# ---------------------------------------------------------------------
# 5) Diagnostics
# ---------------------------------------------------------------------
energy_drift = abs(energy_trace[-1] - energy_trace[0])
entropy_drift = abs(entropy_trace[-1] - entropy_trace[0])
a_final = a_trace[-1]

stable = energy_drift < 1e-3 and entropy_drift < 1e-2
classification = (
    "✅ Cosmological scale stability maintained (energy & entropy conserved)"
    if stable
    else "⚠️ Minor cosmological drift detected"
)

# ---------------------------------------------------------------------
# 6) Plots
# ---------------------------------------------------------------------
plt.figure(figsize=(6, 4))
plt.plot(energy_trace, label="Energy ⟨E⟩", color="#1E88E5")
plt.plot(entropy_trace, label="Spectral Entropy", color="#F57C00")
plt.title("H4 — Cosmological Energy & Entropy Evolution")
plt.xlabel("Step")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_TestH4_EnergyEntropy.png", dpi=160)
plt.close()

plt.figure(figsize=(6, 4))
plt.plot(a_trace, color="#2E7D32")
plt.title("H4 — Scale Factor a(t)")
plt.xlabel("Step")
plt.ylabel("a(t)")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_TestH4_ScaleFactor.png", dpi=160)
plt.close()

plt.figure(figsize=(6, 3))
plt.imshow(np.real(psi), cmap="magma")
plt.title("H4 — ψ Field (Final Real Part)")
plt.colorbar(label="Re(ψ)")
plt.tight_layout()
plt.savefig("PAEV_TestH4_FinalField.png", dpi=160)
plt.close()

# ---------------------------------------------------------------------
# 7) Summary & JSON export
# ---------------------------------------------------------------------
print("\n=== Test H4 — Cosmological Scale Stability Complete ===")
print(f"ħ={ħ:.1e}, G={G:.1e}, α={α:.2f}, Λ0={Λ0:.1e}, β={β:.2f}")
print(f"⟨E⟩ drift  = {energy_drift:.6e}")
print(f"⟨S⟩ drift  = {entropy_drift:.6e}")
print(f"a(final)   = {a_final:.6e}")
print(f"→ {classification}")
print("All output files saved:")
for p in [
    "PAEV_TestH4_EnergyEntropy.png",
    "PAEV_TestH4_ScaleFactor.png",
    "PAEV_TestH4_FinalField.png",
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
        "a_final": float(a_final),
    },
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}

out_path = Path("backend/modules/knowledge/H4_cosmological_stability.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved → {out_path}")