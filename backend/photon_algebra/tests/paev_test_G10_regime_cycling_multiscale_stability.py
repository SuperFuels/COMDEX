import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# ===========================================================
#  G10 — Regime Cycling & Multiscale Stability
# ===========================================================
# Goal:
# Verify smooth transition between quantum, classical, and relativistic regimes.
# The algebra should remain stable as coupling constants vary over orders of magnitude.
# ===========================================================

N = 128
steps = 800
dt = 0.01

x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)

psi = np.exp(-8*(X**2 + Y**2)) * (1 + 0.1*np.random.randn(N,N))
psi_t = np.zeros_like(psi)
kappa = 0.05 * np.exp(-(X**2 + Y**2)/0.2)
kappa_t = np.zeros_like(kappa)

energy_trace, stability_trace, entropy_trace = [], [], []

def laplacian(Z):
    return -4 * Z + np.roll(Z,1,0) + np.roll(Z,-1,0) + np.roll(Z,1,1) + np.roll(Z,-1,1)

def spectral_entropy(field):
    p = np.abs(np.fft.fft2(field))**2
    p /= np.sum(p)
    p = p[p>0]
    return -np.sum(p * np.log(p)) / np.log(len(p))

for step in range(steps):
    # Dynamic regime modulation
    regime_factor = 0.5 + 0.5*np.sin(2*np.pi*step/200)  # oscillates quantum ↔ classical ↔ relativistic
    alpha_q = 0.05 + 0.15*regime_factor
    g_coupling = 0.03 + 0.02*np.cos(2*np.pi*step/150)

    lap_psi = laplacian(psi)
    lap_kappa = laplacian(kappa)

    psi_tt = alpha_q * lap_psi - (psi**3) + g_coupling * kappa * psi
    kappa_tt = 0.07 * lap_kappa + g_coupling * (psi**2 - np.mean(psi**2)) - 0.01*kappa

    psi_t += dt * psi_tt
    psi += dt * psi_t
    kappa_t += dt * kappa_tt
    kappa += dt * kappa_t

    energy = np.mean(psi_t**2 + kappa_t**2)
    stability = np.std(psi) + np.std(kappa)
    entropy = spectral_entropy(psi)

    energy_trace.append(energy)
    stability_trace.append(stability)
    entropy_trace.append(entropy)

# Plot results
plt.figure(figsize=(8,4))
plt.plot(energy_trace, label="Energy")
plt.plot(stability_trace, label="Stability")
plt.legend(); plt.title("G10 — Regime Cycling Energy & Stability")
plt.savefig("PAEV_TestG10_EnergyStability.png")

plt.figure(figsize=(8,4))
plt.plot(entropy_trace, color='darkgreen')
plt.title("Spectral Entropy (ψ) under Regime Cycling")
plt.savefig("PAEV_TestG10_Entropy.png")

print("\n=== Test G10 — Regime Cycling & Multiscale Stability Complete ===")
print(f"⟨E⟩ final = {np.mean(energy_trace[-50:]):.6e}")
print(f"⟨Stability⟩ final = {np.mean(stability_trace[-50:]):.6e}")
print(f"Spectral Entropy final = {np.mean(entropy_trace[-50:]):.6e}")
print("If stability remains bounded across oscillations, transition consistency confirmed.")
print("All output files saved in working directory.")
print("----------------------------------------------------------")