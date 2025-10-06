import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# ===========================================================
#  G9 — Emergent Gravity–Quantum Coupling
# ===========================================================
# Goal:
# Test coupling between curvature field κ and quantum potential ψ,
# to determine if gravity can emerge from quantum coherence collapse.
# ===========================================================

N = 128
steps = 600
dt = 0.01

# Field constants
c1, c2 = 0.13, 0.083
g_coupling = 0.042     # gravitational coupling coefficient
alpha_q = 0.072        # quantum potential scaling
damping = 0.004

x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)

# Initial quantum potential ψ and curvature κ
psi = np.exp(-10 * (X**2 + Y**2)) * (1 + 0.2 * np.random.randn(N, N))
psi_t = np.zeros_like(psi)
kappa = 0.05 * np.exp(-(X**2 + Y**2) / 0.3)
kappa_t = np.zeros_like(kappa)

energy_trace, corr_trace, entropy_trace = [], [], []

def laplacian(Z):
    return -4 * Z + np.roll(Z,1,0) + np.roll(Z,-1,0) + np.roll(Z,1,1) + np.roll(Z,-1,1)

def spectral_entropy(field):
    p = np.abs(np.fft.fft2(field))**2
    p /= np.sum(p)
    p = p[p > 0]
    return -np.sum(p * np.log(p)) / np.log(len(p))

for step in range(steps):
    lap_psi = laplacian(psi)
    lap_kappa = laplacian(kappa)

    # Coupled field equations
    psi_tt = c1 * lap_psi - alpha_q * psi**3 + g_coupling * kappa * psi - damping * psi_t
    kappa_tt = c2 * lap_kappa + g_coupling * (psi**2 - np.mean(psi**2)) - damping * kappa_t

    # Update fields
    psi_t += dt * psi_tt
    psi += dt * psi_t
    kappa_t += dt * kappa_tt
    kappa += dt * kappa_t

    # Diagnostics
    E = np.mean(psi_t**2 + kappa_t**2)
    corr = np.mean(psi * kappa)
    entropy = spectral_entropy(psi)

    energy_trace.append(E)
    corr_trace.append(corr)
    entropy_trace.append(entropy)

# Plots
plt.figure(figsize=(8,4))
plt.plot(energy_trace, label='Energy')
plt.plot(corr_trace, label='ψ·κ Coupling')
plt.legend(); plt.title('G9 — Energy & Coupling Evolution')
plt.savefig('PAEV_TestG9_EnergyCoupling.png')

plt.figure(figsize=(8,4))
plt.plot(entropy_trace, color='purple')
plt.title('Spectral Entropy Evolution (ψ)')
plt.savefig('PAEV_TestG9_SpectralEntropy.png')

np.savez('PAEV_TestG9_Results.npz', E=energy_trace, Corr=corr_trace, S=entropy_trace)

print("\n=== Test G9 — Emergent Gravity–Quantum Coupling Complete ===")
print(f"⟨E⟩ final = {np.mean(energy_trace[-50:]):.6e}")
print(f"⟨ψ·κ⟩ final = {np.mean(corr_trace[-50:]):.6e}")
print(f"Spectral Entropy final = {np.mean(entropy_trace[-50:]):.6e}")
print("Perturbation mode: ON")
print("All output files saved in working directory.")
print("----------------------------------------------------------")