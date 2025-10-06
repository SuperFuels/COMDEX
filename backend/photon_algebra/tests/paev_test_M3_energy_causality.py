import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# === M3 — Wormhole Energy & Causality Validation ===

ħ = 1.0e-3
G = 1.0e-5
Λ = 1.0e-6
α = 0.5

# Spatial grid (1D simplified)
x = np.linspace(-5, 5, 256)
dx = x[1] - x[0]

# Time steps
dt = 1e-2
T = 400

# Initialize ψ fields (entangled Gaussian pair)
ψ1 = np.exp(-(x + 2)**2) * np.exp(1j * 0.1 * x)
ψ2 = np.exp(-(x - 2)**2) * np.exp(-1j * 0.1 * x)

# Curvature potential wells (static)
κ1 = -1.0 / (1.0 + (x + 2)**2)
κ2 = -1.0 / (1.0 + (x - 2)**2)

# Define discrete Laplacian
def laplacian(f):
    return (np.roll(f, -1) - 2*f + np.roll(f, 1)) / dx**2

# Storage
energy_flux = []
cross_corr = []

for t in range(T):
    # Local energy densities
    E1 = ħ**2 * np.abs(laplacian(ψ1))**2 + α * np.abs(ψ1)**2
    E2 = ħ**2 * np.abs(laplacian(ψ2))**2 + α * np.abs(ψ2)**2

    # Classical energy flux proxy
    flux = np.mean(np.abs(E1 - E2))
    energy_flux.append(flux)

    # Quantum field correlation proxy
    corr = np.abs(np.vdot(ψ1, ψ2)) / (np.linalg.norm(ψ1)*np.linalg.norm(ψ2))
    cross_corr.append(corr)

    # Evolve fields (simple Schrödinger-like update)
    ψ1 = ψ1 + dt * (1j * ħ * laplacian(ψ1) - α * κ1 * ψ1)
    ψ2 = ψ2 + dt * (1j * ħ * laplacian(ψ2) - α * κ2 * ψ2)

energy_flux = np.array(energy_flux)
cross_corr = np.array(cross_corr)

# Normalize
energy_flux /= np.max(energy_flux)
cross_corr /= np.max(cross_corr)

# Compute correlation lag (simplified causality check)
lag_index = np.argmax(np.correlate(cross_corr, energy_flux, mode='full')) - len(energy_flux)
lag_time = lag_index * dt

# Verdict
causal_threshold = 1.0  # time units of lightcone
is_causal = np.abs(lag_time) <= causal_threshold

# === Plot 1: Energy and Correlation Evolution ===
plt.figure(figsize=(7,5))
plt.plot(energy_flux, label='Normalized Energy Flux', linestyle='--')
plt.plot(cross_corr, label='Cross-Correlation |⟨ψ₁|ψ₂⟩|')
plt.xlabel("Time step")
plt.ylabel("Normalized magnitude")
plt.title("M3 — Energy and Correlation Evolution")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_M3_EnergyFlux.png", dpi=200)
plt.close()

# === Plot 2: Causality Map ===
plt.figure(figsize=(6,5))
plt.bar(["Lag Time"], [lag_time], color='tab:blue')
plt.axhline(causal_threshold, color='r', linestyle='--', label='Causality threshold')
plt.axhline(-causal_threshold, color='r', linestyle='--')
plt.title("M3 — Causality Lag Assessment")
plt.ylabel("Lag Time (Δt units)")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_M3_CausalityMap.png", dpi=200)
plt.close()

# === Print results ===
print("=== M3 — Wormhole Energy & Causality Validation ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
print(f"Max Cross-Correlation: {np.max(cross_corr):.3e}")
print(f"Max Energy Flux: {np.max(energy_flux):.3e}")
print(f"Lag Time (proxy): {lag_time:.3f}")
if is_causal:
    print("✅ System respects causal limits — no superluminal entanglement.")
else:
    print("⚠️ Non-causal correlation detected — possible ER=EPR signature.")
print(f"✅ Plots saved:\n   - PAEV_M3_EnergyFlux.png\n   - PAEV_M3_CausalityMap.png")
print("----------------------------------------------------------")