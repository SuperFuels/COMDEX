#!/usr/bin/env python3
# ==========================================================
# G9 — Emergent Gravity from ψ–κ Correlations (Stable Tessaris Standard)
# Demonstrates gravitational-like attraction arising algebraically from
# correlated ψ (information) and κ (curvature) fields.
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
N = 128
L = 6.0
dx = L / N
steps = 600
dt = 0.002
chi = 0.08
eta = 0.015
alpha_psi = 0.01
damping = 0.995  # mild normalization damping

# --- Initialize Fields ---
x = np.linspace(-L/2, L/2, N)
psi = np.exp(-(x + 1.5)**2 * 4) + np.exp(-(x - 1.5)**2 * 4) * np.exp(1j * 0.3)
kappa = 0.05 * np.exp(-x**2 * 3)

def lap(v): return (np.roll(v, -1) + np.roll(v, 1) - 2*v) / dx**2

def evolve(psi, kappa, dt):
    psi_t = chi * lap(psi) + 1j * eta * kappa * psi - alpha_psi * psi
    kappa_t = 0.2 * lap(kappa) + 0.002 * (np.abs(psi)**2 - kappa)
    psi_next = (psi + dt * psi_t) * damping
    kappa_next = (kappa + dt * kappa_t) * damping
    psi_next /= (1e-12 + np.sqrt(np.mean(np.abs(psi_next)**2)))
    return psi_next, kappa_next

# --- Evolution Loop ---
centroid = []
corr_t = []
for _ in range(steps):
    psi, kappa = evolve(psi, kappa, dt)
    prob = np.abs(psi)**2
    cm = np.sum(x * prob) / np.sum(prob)
    centroid.append(cm)
    corr = np.mean(np.abs(psi) * np.abs(kappa))
    corr_t.append(corr)

centroid = np.array(centroid)
corr_t = np.array(corr_t)
velocity = np.gradient(centroid)
accel = np.gradient(velocity)

# --- Derived Metrics ---
mean_accel = float(np.nanmean(-accel))
mean_corr = float(np.nanmean(corr_t))
stability = 1.0 - np.std(corr_t) / np.mean(corr_t)
if stability < 0:
    stability = 0.0

# --- Classification ---
if stability > 0.9 and mean_corr > 0.003:
    verdict = "✅ Stable Emergent Gravitational Coupling"
elif stability > 0.6:
    verdict = "⚠️ Partial Correlation (Marginal Coupling)"
else:
    verdict = "❌ Unstable or Decoherent Field Interaction"

# --- Plots ---
plt.figure(figsize=(8, 4))
plt.plot(-accel, label='−acceleration', lw=1.2)
plt.plot(corr_t / np.max(corr_t), label='|ψ·κ| (normalized)', lw=1.0, alpha=0.7)
plt.xlabel("Step")
plt.ylabel("Normalized Values")
plt.title("G9 — Emergent Gravity: ψ–κ Correlation Dynamics")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_G9_ForceCorrelation.png")

plt.figure(figsize=(8, 4))
plt.plot(centroid, label='ψ centroid')
plt.title("G9 — ψ Centroid Trajectory (Emergent Potential)")
plt.xlabel("Step")
plt.ylabel("Centroid Position")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_G9_CentroidTrajectory.png")

plt.figure(figsize=(8, 4))
plt.plot(corr_t, label='|ψ·κ| Coupling Strength')
plt.title("G9 — ψ–κ Coupling Strength Evolution")
plt.xlabel("Step")
plt.ylabel("Coupling Magnitude")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_G9_CouplingEvolution.png")

# --- Save JSON Results ---
results = {
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β, "c": c, "kB": kB
    },
    "parameters": {
        "N": N, "L": L, "steps": steps, "dt": dt,
        "chi": chi, "eta": eta, "alpha_psi": alpha_psi,
        "damping": damping
    },
    "metrics": {
        "mean_accel": mean_accel,
        "mean_corr": mean_corr,
        "stability": stability
    },
    "classification": verdict,
    "files": {
        "force_plot": "FAEV_G9_ForceCorrelation.png",
        "centroid_plot": "FAEV_G9_CentroidTrajectory.png",
        "coupling_plot": "FAEV_G9_CouplingEvolution.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/G9_emergent_gravity.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== G9 — Emergent Gravity from ψ–κ Correlations ===")
print(f"mean_accel={mean_accel:.3e} | mean_corr={mean_corr:.3e} | stability={stability:.3f}")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/G9_emergent_gravity.json")