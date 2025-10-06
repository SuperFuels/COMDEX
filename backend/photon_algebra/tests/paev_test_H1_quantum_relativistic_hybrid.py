# backend/photon_algebra/tests/paev_test_H1_quantum_relativistic_hybrid_stable.py
"""
Test H1 (Stabilized) — Quantum–Relativistic Hybrid Field
Goal: Couple ψ (quantum) and κ (relativistic curvature) in a balanced regime.
This is a stable version of the original H1 test with renormalized coupling.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# --- Parameters ---
N = 128
steps = 600
dt = 0.01
gamma = 0.1          # quantum-relativistic coupling scale
curv_coupling = 0.01 # reduced from 0.15 → stabilizes feedback
damping = 0.002      # small energy dissipation term

# --- Initialize Fields ---
x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)

# Quantum field ψ (wavefunction) and curvature κ
psi = np.exp(-5 * (X**2 + Y**2)) * np.exp(1j * 5 * X)
kappa = 0.05 * np.exp(-8 * (X**2 + Y**2))
energy_trace, coupling_trace, entropy_trace = [], [], []

def laplacian(Z):
    return -4*Z + np.roll(Z,1,0) + np.roll(Z,-1,0) + np.roll(Z,1,1) + np.roll(Z,-1,1)

# --- Main Evolution Loop ---
for step in range(steps):
    lap_psi = laplacian(psi)
    lap_kappa = laplacian(kappa)
    
    # ψ evolution (quantum)
    psi_t = (1j * dt) * (lap_psi - kappa * psi) * gamma
    psi += psi_t - damping * psi * dt

    # κ evolution (relativistic curvature)
    kappa_t = dt * (0.05 * lap_kappa + curv_coupling * np.abs(psi)**2 - 0.02 * kappa)
    kappa += kappa_t

    # --- Diagnostics ---
    spectral_density = np.abs(np.fft.fftshift(np.fft.fft2(psi)))**2
    p_norm = spectral_density / (np.sum(spectral_density) + 1e-12)
    entropy = -np.sum(p_norm * np.log(p_norm + 1e-12))
    
    energy = np.mean(np.abs(psi)**2 + np.abs(kappa)**2)
    coupling = np.mean(np.real(psi) * kappa)
    
    energy_trace.append(energy)
    coupling_trace.append(coupling)
    entropy_trace.append(entropy)
    
    if step % 100 == 0:
        print(f"Step {step:03d} — ⟨E⟩={energy:.4e}, ⟨ψ·κ⟩={coupling:.4e}, S={entropy:.4f}")

# --- Save Outputs ---
plt.figure()
plt.plot(energy_trace, label="Energy ⟨E⟩")
plt.plot(coupling_trace, label="Coupling ⟨ψ·κ⟩")
plt.legend(); plt.title("H1 — Energy & Coupling Trace (Stabilized)")
plt.xlabel("Steps"); plt.ylabel("Value")
plt.savefig("PAEV_TestH1_EnergyCoupling_Stable.png", dpi=150)

plt.figure()
plt.plot(entropy_trace, color="purple")
plt.title("H1 — Spectral Entropy (Stabilized Quantum–Relativistic Field)")
plt.xlabel("Steps"); plt.ylabel("Entropy")
plt.savefig("PAEV_TestH1_SpectralEntropy_Stable.png", dpi=150)

plt.figure()
plt.imshow(np.real(psi), cmap="plasma")
plt.title("H1 — Final ψ Field (Real Part)")
plt.colorbar()
plt.savefig("PAEV_TestH1_FieldSnapshot_Stable.png", dpi=150)

# --- Summary Output ---
print("\n=== Test H1 (Stabilized) — Quantum–Relativistic Hybrid Complete ===")
print(f"⟨E⟩ final = {energy_trace[-1]:.6e}")
print(f"⟨ψ·κ⟩ final = {coupling_trace[-1]:.6e}")
print(f"Spectral Entropy final = {entropy_trace[-1]:.6e}")
print("All output files saved:")
print(" - PAEV_TestH1_EnergyCoupling_Stable.png")
print(" - PAEV_TestH1_SpectralEntropy_Stable.png")
print(" - PAEV_TestH1_FieldSnapshot_Stable.png")
print("----------------------------------------------------------")