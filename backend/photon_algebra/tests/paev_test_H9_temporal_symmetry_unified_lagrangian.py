"""
Test H9.1 - Stabilized Temporal Symmetry & Unified Lagrangian Closure
--------------------------------------------------------------------
Models ψ-κ-T interaction with temporal reversal (dt -> -dt)
and applies normalization + damping to prevent overflow.
Goal: Achieve reversible energy and entropy closure.
"""

import numpy as np
import matplotlib.pyplot as plt
from numpy.fft import fft2, fftshift

# ---------------------------------------------
# Laplacian Operator
# ---------------------------------------------
def laplacian_2d(field):
    return (
        np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0) +
        np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1) -
        4 * field
    )

# ---------------------------------------------
# Parameters
# ---------------------------------------------
N = 128
steps = 800
dt = 0.005
damping = 0.001

# Initialize all as COMPLEX128
x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)
psi = np.exp(-25 * (X**2 + Y**2)).astype(np.complex128)
kappa = np.zeros_like(psi, dtype=np.complex128)
tensor = np.zeros_like(psi, dtype=np.complex128)

E_vals, coupling_vals, coherence_vals, S_vals = [], [], [], []

# ---------------------------------------------
# Evolution Loop
# ---------------------------------------------
for step in range(steps):
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)
    lap_T = laplacian_2d(tensor)

    # Unified Lagrangian dynamics (time-symmetric)
    psi_t = 1j * (lap_psi - kappa * psi + 0.05 * tensor * np.conj(psi)) - damping * psi
    kappa_t = 0.02 * (lap_kappa - np.abs(psi)**2)
    T_t = 0.01 * (lap_T - np.abs(kappa)**2)

    # Integrate
    psi = psi + dt * psi_t
    kappa = kappa + dt * kappa_t
    tensor = tensor + dt * T_t

    # Renormalize ψ to prevent runaway
    psi /= np.sqrt(np.mean(np.abs(psi)**2) + 1e-12)

    # Safety clamp
    if np.any(np.isnan(psi)) or np.any(np.abs(psi) > 10):
        psi *= 0.1
        kappa *= 0.1
        tensor *= 0.1

    # Measure quantities
    energy = np.mean(np.abs(psi)**2 + np.abs(kappa)**2 + np.abs(tensor)**2)
    coupling = np.mean(np.real(psi) * np.real(kappa))
    coherence = np.mean(np.real(psi) * np.real(tensor))

    spectral_density = np.abs(fftshift(fft2(psi)))**2
    p_norm = spectral_density / np.sum(spectral_density)
    spectral_entropy = -np.sum(p_norm * np.log(p_norm + 1e-12))

    E_vals.append(energy)
    coupling_vals.append(coupling)
    coherence_vals.append(coherence)
    S_vals.append(spectral_entropy)

    # Temporal reversal midway
    if step == steps // 2:
        dt *= -1  # reverse time direction

    if step % 100 == 0:
        print(f"Step {step:03d} - ⟨E⟩={energy:.5f}, ⟨ψ*κ⟩={coupling:.5e}, ⟨ψ*T⟩={coherence:.5e}, S={spectral_entropy:.5f}")

# ---------------------------------------------
# Results Summary
# ---------------------------------------------
print("\n=== Test H9.1 - Stabilized Temporal Symmetry Closure Complete ===")
print(f"⟨E⟩ drift = {E_vals[-1] - E_vals[0]:.5e}")
print(f"⟨S⟩ drift = {S_vals[-1] - S_vals[0]:.5e}")
print(f"Final Coupling = {coupling_vals[-1]:.5e}")
print(f"Final Coherence = {coherence_vals[-1]:.5e}")
print("All output files saved:")

# ---------------------------------------------
# Plot Results
# ---------------------------------------------
plt.figure()
plt.plot(E_vals, label="Energy ⟨E⟩")
plt.plot(coupling_vals, label="ψ*κ Coupling")
plt.plot(coherence_vals, label="ψ*T Coherence")
plt.title("H9.1 - Temporal Symmetry Closure (Energy & Couplings)")
plt.xlabel("Step")
plt.ylabel("Value")
plt.legend()
plt.savefig("PAEV_TestH9_Stable_EnergyCoupling.png")

plt.figure()
plt.plot(S_vals, color='purple')
plt.title("H9.1 - Spectral Entropy Evolution")
plt.xlabel("Step")
plt.ylabel("Entropy")
plt.savefig("PAEV_TestH9_Stable_SpectralEntropy.png")

plt.figure()
plt.imshow(np.real(psi), cmap="magma")
plt.colorbar(label="Re(ψ)")
plt.title("H9.1 - Final ψ Field (Stable Regime)")
plt.savefig("PAEV_TestH9_Stable_FinalField.png")

print(" - PAEV_TestH9_Stable_EnergyCoupling.png")
print(" - PAEV_TestH9_Stable_SpectralEntropy.png")
print(" - PAEV_TestH9_Stable_FinalField.png")
print("----------------------------------------------------------")