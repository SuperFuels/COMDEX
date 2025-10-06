import numpy as np
import matplotlib.pyplot as plt
from numpy.fft import fftshift, fft2

def laplacian_2d(field):
    return (
        -4 * field
        + np.roll(field, 1, 0)
        + np.roll(field, -1, 0)
        + np.roll(field, 1, 1)
        + np.roll(field, -1, 1)
    )

N = 128
steps = 700
dt = 0.02

psi = np.exp(-((np.linspace(-3,3,N)[:,None])**2 + (np.linspace(-3,3,N)[None,:])**2)) * (1+0.1j)
kappa = np.zeros((N,N))
tensor = np.zeros((N,N))

alpha, beta, gamma = 0.05, 0.01, 0.02  # coupling strengths
damping = 0.995  # small global damping

E_vals, coupling_vals, coherence_vals, entropy_vals = [], [], [], []

for t in range(steps):
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)
    lap_T = laplacian_2d(tensor)

    psi_t = 1j * (lap_psi - kappa * psi + alpha * tensor * psi)
    kappa_t = beta * (lap_kappa - np.abs(psi)**2 + gamma * tensor)
    T_t = 0.005 * (lap_T - np.abs(kappa)**2)

    psi += dt * psi_t
    kappa += dt * kappa_t
    tensor += dt * T_t

    # Normalization and damping
    psi /= np.sqrt(np.mean(np.abs(psi)**2) + 1e-9)
    tensor = np.clip(tensor, -1.0, 1.0)
    kappa *= damping
    tensor *= damping

    # Diagnostics
    energy = np.mean(np.abs(psi)**2 + np.abs(kappa)**2 + np.abs(tensor)**2)
    coupling = np.mean(np.real(psi) * kappa)
    coherence = np.mean(np.real(psi) * tensor)
    spectral_density = np.abs(fftshift(fft2(psi)))**2
    p_norm = spectral_density / np.sum(spectral_density)
    entropy = -np.sum(p_norm * np.log(p_norm + 1e-10))

    E_vals.append(energy)
    coupling_vals.append(coupling)
    coherence_vals.append(coherence)
    entropy_vals.append(entropy)

    if t % 100 == 0:
        print(f"Step {t:03d} — ⟨E⟩={energy:.5f}, ⟨ψ·κ⟩={coupling:.5f}, ⟨ψ·T⟩={coherence:.5f}, S={entropy:.5f}")

plt.figure(figsize=(7,5))
plt.plot(E_vals, label="Energy ⟨E⟩")
plt.plot(coupling_vals, label="ψ·κ Coupling")
plt.plot(coherence_vals, label="ψ·T Coherence")
plt.title("H8.1 — Stabilized Unified Field Tensor Coupling")
plt.xlabel("Step")
plt.ylabel("Value")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestH8_Stable_EnergyCoupling.png")

plt.figure(figsize=(6,5))
plt.plot(entropy_vals, color='purple')
plt.title("H8.1 — Spectral Entropy Evolution")
plt.xlabel("Step")
plt.ylabel("Entropy")
plt.tight_layout()
plt.savefig("PAEV_TestH8_Stable_SpectralEntropy.png")

plt.figure(figsize=(6,5))
plt.imshow(np.real(psi), cmap="magma")
plt.colorbar(label="Re(ψ)")
plt.title("H8.1 — Final ψ Field (Stable Regime)")
plt.tight_layout()
plt.savefig("PAEV_TestH8_Stable_FinalField.png")

print("\n=== Test H8.1 — Stabilized Quantum–Gravitational Coupling Complete ===")
print(f"⟨E⟩ final = {E_vals[-1]:.6e}")
print(f"⟨ψ·κ⟩ final = {coupling_vals[-1]:.6e}")
print(f"⟨ψ·T⟩ final = {coherence_vals[-1]:.6e}")
print(f"Spectral Entropy final = {entropy_vals[-1]:.6e}")
print("All output files saved:")
print(" - PAEV_TestH8_Stable_EnergyCoupling.png")
print(" - PAEV_TestH8_Stable_SpectralEntropy.png")
print(" - PAEV_TestH8_Stable_FinalField.png")
print("----------------------------------------------------------")