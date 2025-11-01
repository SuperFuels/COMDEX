import numpy as np
import matplotlib.pyplot as plt
from numpy.fft import fft2, fftshift

def laplacian_2d(field):
    return (
        np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0) +
        np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1) - 4 * field
    )

# Simulation parameters
N = 128
dt = 0.01
steps = 800

# Initialize fields
x = np.linspace(-4, 4, N)
X, Y = np.meshgrid(x, x)
psi = np.exp(-(X**2 + Y**2)) * np.exp(1j * 0.05 * (X + Y))
kappa = 0.05 * np.real(psi)
tensor = 0.01 * np.real(psi)

# Holographic feedback parameters
feedback_gain = 0.02
causal_lag = 3
psi_hist = [psi.copy() for _ in range(causal_lag)]

energies, couplings, coherences, entropies, holography = [], [], [], [], []

for t in range(steps):
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)
    lap_T = laplacian_2d(tensor)

    psi_t = 1j * (lap_psi - kappa * psi + 0.05 * tensor * np.conj(psi))
    kappa_t = 0.02 * (lap_kappa - np.abs(psi)**2)
    T_t = 0.01 * (lap_T - np.abs(kappa)**2 + 0.001 * np.real(psi))

    # Causal feedback (boundary holographic constraint)
    psi_feedback = psi_hist[-1] - psi_hist[0]
    psi += dt * (psi_t + feedback_gain * psi_feedback)
    kappa += dt * kappa_t
    tensor += dt * T_t

    psi_hist.append(psi.copy())
    psi_hist.pop(0)

    energy = np.mean(np.abs(psi)**2 + np.abs(kappa)**2 + np.abs(tensor)**2)
    coupling = np.mean(np.real(psi) * kappa)
    coherence = np.mean(np.real(psi) * tensor)

    spectral_density = np.abs(fftshift(fft2(psi)))**2
    p_norm = spectral_density / np.sum(spectral_density)
    entropy = -np.sum(p_norm * np.log(p_norm + 1e-12))

    holo_corr = np.mean(np.real(psi_feedback) * np.real(psi))
    
    energies.append(energy)
    couplings.append(coupling)
    coherences.append(coherence)
    entropies.append(entropy)
    holography.append(holo_corr)

    if t % 100 == 0:
        print(f"Step {t:03d} - ⟨E⟩={energy:.5f}, ⟨ψ*κ⟩={coupling:.5f}, ⟨ψ*T⟩={coherence:.5f}, S={entropy:.5f}, C_H={holo_corr:.5f}")

print("\n=== Test H10 - Causal-Entropic Holographic Equilibrium Complete ===")
print(f"⟨E⟩ final = {energies[-1]:.6e}")
print(f"⟨ψ*κ⟩ final = {couplings[-1]:.6e}")
print(f"⟨ψ*T⟩ final = {coherences[-1]:.6e}")
print(f"Spectral Entropy final = {entropies[-1]:.6e}")
print(f"Holographic Correlation final = {holography[-1]:.6e}")

# Plot energy, couplings, coherence
plt.figure()
plt.plot(energies, label="Energy ⟨E⟩")
plt.plot(couplings, label="ψ*κ Coupling")
plt.plot(coherences, label="ψ*T Coherence")
plt.title("H10 - Causal-Entropic Energy & Coupling Evolution")
plt.xlabel("Step")
plt.ylabel("Value")
plt.legend()
plt.savefig("PAEV_TestH10_EnergyCoupling.png")

# Plot entropy
plt.figure()
plt.plot(entropies, color="purple", label="Spectral Entropy")
plt.title("H10 - Spectral Entropy Evolution")
plt.xlabel("Step")
plt.ylabel("Entropy")
plt.legend()
plt.savefig("PAEV_TestH10_SpectralEntropy.png")

# Plot holographic correlation
plt.figure()
plt.plot(holography, color="teal", label="Holographic Correlation")
plt.title("H10 - Holographic Information Stability")
plt.xlabel("Step")
plt.ylabel("C_H")
plt.legend()
plt.savefig("PAEV_TestH10_HolographicCorrelation.png")

# Field visualization
plt.figure()
plt.imshow(np.real(psi), cmap="magma")
plt.colorbar(label="Re(ψ)")
plt.title("H10 - Final ψ Field (Holographic Equilibrium)")
plt.savefig("PAEV_TestH10_FinalField.png")

plt.close("all")