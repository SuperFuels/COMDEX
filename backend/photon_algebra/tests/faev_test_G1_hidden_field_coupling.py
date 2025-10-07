# ==========================================================
# G1 — Hidden Field Coupling (Dual Curvature Interaction)
# First test of dark-sector field ψ coupled to visible curvature R
# ==========================================================

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from backend.photon_algebra.utils.load_constants import load_constants

# --- Load Unified Constants ---
const = load_constants()
ħ = const.get("ħ", 1.054571817e-34)
G = const.get("G", 6.67430e-11)
Λ = const.get("Λ", 0.0018)
α = const.get("α", 0.7)
β = const.get("β", 0.08)
c = const.get("c", 2.99792458e8)
kB = const.get("kB", 1.380649e-23)

# --- Simulation Parameters ---
np.random.seed(42)
T = 4000
dt = 0.002
alpha_psi = const.get("alpha_psi", 0.025)  # hidden field coupling strength
omega0 = const.get("omega0", 0.18)
noise = const.get("noise", 0.0006)

# --- Initialize Fields ---
t = np.linspace(0, T*dt, T)
phi = np.zeros(T)     # visible field
psi = np.zeros(T)     # hidden field
R = np.zeros(T)       # visible curvature
R_psi = np.zeros(T)   # hidden curvature
energy = np.zeros(T)

phi[0] = 0.01
psi[0] = 0.02

# --- Evolution Loop ---
for i in range(1, T):
    # Hidden field ψ evolves with visible curvature coupling
    dpsi = -alpha_psi * R[i-1] + β * np.sin(phi[i-1]) - 0.01 * psi[i-1]
    psi[i] = psi[i-1] + dpsi * dt

    # Visible curvature with hidden feedback
    R[i] = np.sin(omega0 * t[i]) + alpha_psi * psi[i-1]
    R_psi[i] = np.sin(omega0 * t[i] + np.pi/4) - alpha_psi * phi[i-1]

    # Visible field φ feedback
    dphi = -omega0**2 * phi[i-1] - β * phi[i-1]**3 + alpha_psi * psi[i-1]
    phi[i] = phi[i-1] + dphi * dt + np.random.normal(0, noise)

    # Energy density (unified form)
    energy[i] = (c**4 / (8 * np.pi * G)) * (R[i] + alpha_psi * R_psi[i]) \
                + kB * 300 * np.abs(phi[i]) + ħ * (psi[i]**2)

# --- Metrics ---
cross_corr = float(np.corrcoef(R, R_psi)[0, 1])
stability = 1.0 - np.std(energy) / np.mean(np.abs(energy))
energy_min = float(np.min(energy))
energy_max = float(np.max(energy))

# --- Classification ---
if stability > 0.85 and abs(cross_corr) > 0.7:
    verdict = "✅ Coherent Hidden–Visible Coupling"
elif stability > 0.6:
    verdict = "⚠️ Weak or Partial Coupling"
else:
    verdict = "❌ Unstable Interaction (Decoupled Fields)"

# --- Plots ---
plt.figure(figsize=(9, 5))
plt.plot(t, R, label='Visible curvature R', lw=1.2)
plt.plot(t, R_psi, label='Hidden curvature Rψ', lw=1.0, alpha=0.7)
plt.title("G1 — Hidden Field Coupling Dynamics")
plt.xlabel("time"); plt.ylabel("curvature")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1_CurvatureEvolution.png")

plt.figure(figsize=(9, 5))
plt.plot(t, energy, label='Unified energy density', lw=1.2)
plt.title("G1 — Unified Energy Evolution")
plt.xlabel("time"); plt.ylabel("E_total")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1_EnergyEvolution.png")

plt.figure(figsize=(9, 5))
plt.plot(t, np.cos(phi), label='cos(φ)', lw=1.0)
plt.plot(t, np.cos(psi), label='cos(ψ)', lw=1.0, alpha=0.7)
plt.title("G1 — Phase Coherence Between φ and ψ")
plt.xlabel("time"); plt.ylabel("cosine phase")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1_PhaseCoherence.png")

# --- Save JSON Results ---
results = {
    "dt": dt,
    "T": T,
    "constants": {
        "ħ": ħ,
        "G": G,
        "Λ": Λ,
        "α": α,
        "β": β,
        "alpha_psi": alpha_psi,
        "omega0": omega0,
        "noise": noise
    },
    "metrics": {
        "cross_correlation_R_Rpsi": cross_corr,
        "energy_stability": float(stability),
        "energy_min": energy_min,
        "energy_max": energy_max
    },
    "classification": verdict,
    "files": {
        "curvature_plot": "FAEV_G1_CurvatureEvolution.png",
        "energy_plot": "FAEV_G1_EnergyEvolution.png",
        "phase_plot": "FAEV_G1_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/G1_hidden_field_coupling.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== G1 — Hidden Field Coupling (Dual Curvature Interaction) ===")
print(f"cross_corr={cross_corr:.3f} | stability={stability:.3f} | energy=({energy_min:.3e},{energy_max:.3e})")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/G1_hidden_field_coupling.json")