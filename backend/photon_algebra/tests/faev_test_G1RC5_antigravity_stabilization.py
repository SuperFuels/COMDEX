# ==========================================================
# G1-RC5 - Antigravity / Negative-Mass Balancing Stabilization
# Final refinement of G1 hidden-field coupling.
# Introduces selective curvature inversion when |R - Rψ| exceeds threshold.
# ==========================================================

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- Constants Loader ---
try:
    from backend.photon_algebra.utils.load_constants import load_constants
    const = load_constants()
except Exception:
    const = {
        "ħ": 1e-3, "G": 1e-5, "Λ": 1e-6, "α": 0.5, "β": 0.2,
        "omega0": 0.18, "noise": 6e-4
    }

ħ, G, Λ, α, β = const.get("ħ", 1e-3), const.get("G", 1e-5), const.get("Λ", 1e-6), const.get("α", 0.5), const.get("β", 0.2)
omega0, noise = const.get("omega0", 0.18), const.get("noise", 6e-4)

# --- Simulation Parameters ---
np.random.seed(42)
T = 4000
dt = 0.002
t = np.linspace(0, T*dt, T)

# --- Stabilization Parameters ---
k_sync = 0.04      # adaptive coupling gain
k_damp = 0.02      # energy damping
k_info = 0.004     # phase information transfer
nu = 0.015         # antigravity feedback strength
threshold = 0.15   # activation for negative-mass response
phi_damp = 0.0025
psi_gain = 1.05
gamma = 0.0045
mu = 0.02

# --- Initialize Arrays ---
R = np.zeros(T)
Rψ = np.zeros(T)
φ = np.zeros(T)
ψ = np.zeros(T)
E = np.zeros(T)
R[0], Rψ[0] = 0.0, 0.7
φ[0], ψ[0] = 0.0, 0.01

# --- Simulation Loop ---
for i in range(1, T):
    # --- Phase evolution with information feedback ---
    dφ = (omega0 - phi_damp * np.sin(φ[i-1])) * dt + np.random.normal(0, noise)
    dψ = (omega0 + k_info * np.sin(φ[i-1] - ψ[i-1])) * dt + np.random.normal(0, noise * 0.5)
    φ[i] = φ[i-1] + dφ
    ψ[i] = ψ[i-1] + dψ

    # --- Adaptive curvature coupling ---
    div = R[i-1] - Rψ[i-1]
    g_adapt = k_sync * (1 + 0.5 * np.abs(np.sin(φ[i-1] - ψ[i-1])))

    # --- Curvature evolution ---
    dR = α * 0.15 + mu * Rψ[i-1] - gamma * R[i-1] - 0.02 * R[i-1] ** 3 + g_adapt * div
    dRψ = β * 0.12 + mu * R[i-1] - gamma * Rψ[i-1] - 0.02 * Rψ[i-1] ** 3 - g_adapt * div

    # --- Antigravity (Negative-Mass) Correction ---
    if abs(div) > threshold:
        correction = -nu * np.sign(div) * abs(div)
        Rψ[i-1] += correction

    # --- Energy damping ---
    E_geom = (1.0 / (8 * np.pi * max(G, 1e-12))) * (R[i-1] + Rψ[i-1])
    E_th = np.abs(np.cos(φ[i-1])) * 0.25
    E_info = ħ * np.abs(np.sin(φ[i-1] - ψ[i-1]))
    E_total = E_geom + E_th + E_info

    dE = -k_damp * E_total
    E[i] = E[i-1] + dE * dt + E_total * dt * 0.1

    # --- Integrate curvature ---
    R[i] = R[i-1] + dt * dR
    Rψ[i] = Rψ[i-1] + dt * (dRψ * psi_gain)

# --- Metrics ---
cross_corr = float(np.corrcoef(R, Rψ)[0, 1])
stability = 1.0 / (1.0 + np.std(E) / (np.mean(np.abs(E)) + 1e-9))
energy_min = float(np.min(E))
energy_max = float(np.max(E))

# --- Classification ---
if stability > 0.85 and cross_corr > 0.8:
    verdict = "✅ Coherent Hidden-Visible Coupling (Stable Equilibrium)"
elif stability > 0.6:
    verdict = "⚠️ Partially Coupled (Marginally Stable)"
else:
    verdict = "❌ Unstable Interaction (Decoupled Fields)"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, R, label="Visible curvature R", lw=1.2)
plt.plot(t, Rψ, label="Hidden curvature Rψ", lw=1.0, alpha=0.8)
plt.title("G1-RC5 - Hidden Field Coupling (Antigravity Stabilization)")
plt.xlabel("time"); plt.ylabel("curvature")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1RC5_CurvatureEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(t, E, label="Unified energy (stabilized)", lw=1.2)
plt.title("G1-RC5 - Unified Energy Evolution (Balanced via Antigravity)")
plt.xlabel("time"); plt.ylabel("E_total (norm)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1RC5_EnergyEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(t, np.cos(φ), label="cos(φ)", lw=1.0)
plt.plot(t, np.cos(ψ), label="cos(ψ)", lw=1.0, alpha=0.8)
plt.title("G1-RC5 - Phase Coherence Between φ and ψ (Balanced)")
plt.xlabel("time"); plt.ylabel("cosine phase")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1RC5_PhaseCoherence.png")

# --- Save JSON Results ---
results = {
    "dt": dt,
    "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "omega0": omega0, "noise": noise,
        "k_sync": k_sync, "k_damp": k_damp,
        "k_info": k_info, "nu": nu, "threshold": threshold,
        "phi_damp": phi_damp, "psi_gain": psi_gain,
        "gamma": gamma, "mu": mu
    },
    "metrics": {
        "cross_correlation_R_Rψ": cross_corr,
        "energy_stability": stability,
        "energy_min": energy_min,
        "energy_max": energy_max
    },
    "classification": verdict,
    "files": {
        "curvature_plot": "FAEV_G1RC5_CurvatureEvolution.png",
        "energy_plot": "FAEV_G1RC5_EnergyEvolution.png",
        "phase_plot": "FAEV_G1RC5_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/G1RC5_antigravity_stabilization.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== G1-RC5 - Antigravity / Negative-Mass Balancing Stabilization ===")
print(f"cross_corr={cross_corr:.3f} | stability={stability:.3f} | energy=({energy_min:.3e},{energy_max:.3e})")
print(f"-> {verdict}")
print("✅ Results saved -> backend/modules/knowledge/G1RC5_antigravity_stabilization.json")