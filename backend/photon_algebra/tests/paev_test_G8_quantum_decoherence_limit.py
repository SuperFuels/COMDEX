"""
PAEV Test G8 — Quantum Decoherence Limit
----------------------------------------
This test models the transition from coherent photon–curvature coupling
to quantum decoherence. It tracks phase–curvature correlation decay,
entropy rise, and ψ-spectrum broadening as coherence is lost.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from numpy.fft import fft2, fftshift

np.random.seed(42)
print("💫 Initiating G8 — Quantum Decoherence Limit Test...")
print("💥 Perturbation mode enabled — simulating decoherence transition.")

# === PARAMETERS ===
N = 96
steps = 320
dt = 0.01
c1, c2, c3 = 0.15, 0.10, 0.08
theta = np.zeros((N, N))
kappa = np.zeros_like(theta)
phase = np.random.normal(0, 0.01, (N, N))
coherence = []

def laplacian(Z):
    return (-4 * Z +
            np.roll(Z, 1, 0) + np.roll(Z, -1, 0) +
            np.roll(Z, 1, 1) + np.roll(Z, -1, 1))

def spectral_entropy(field):
    fft_mag = np.abs(fft2(field))**2
    p = fft_mag / np.sum(fft_mag)
    p = p[p > 0]
    return -np.sum(p * np.log(p)) / np.log(len(p))

# === STORAGE ===
energy_trace, entropy_trace, corr_trace = [], [], []
var_phi_trace = []

for t in range(steps):
    lap_t = laplacian(theta)
    lap_k = laplacian(kappa)
    noise = np.random.normal(0, 0.0025, (N, N))
    decay = np.exp(-t / (steps / 3))  # coherence decay envelope

    theta_t = c1 * lap_k - c3 * theta + noise * decay
    kappa_t = c2 * lap_t - c3 * kappa + noise

    theta += dt * theta_t
    kappa += dt * kappa_t

    dphi = np.gradient(theta)[0]
    var_phi = np.var(dphi)
    var_phi_trace.append(var_phi)

    energy = np.nanmean(theta**2 + kappa**2)
    entropy = spectral_entropy(theta)
    corr = np.corrcoef(dphi.flatten(), kappa.flatten())[0, 1]

    energy_trace.append(energy)
    entropy_trace.append(entropy)
    corr_trace.append(corr)

# === RESULTS ===
corr_final = np.nanmean(corr_trace[-10:])
entropy_final = np.nanmean(entropy_trace[-10:])
energy_final = np.nanmean(energy_trace[-10:])

print(f"\n=== Test G8 — Quantum Decoherence Limit Complete ===")
print(f"⟨ℒ⟩ (proxy) final = {energy_final:.6e}")
print(f"S (final)         = {entropy_final:.6f}")
print(f"Var(Δφ) (final)   = {np.mean(var_phi_trace[-10:]):.6e}")
print(f"corr(Δφ, κ) final = {corr_final:.3f}")
print("----------------------------------------------------------")

# === VISUALIZATION ===
fig, ax1 = plt.subplots(figsize=(8,5))
ax1.plot(energy_trace, label="⟨ℒ⟩ proxy", color="royalblue")
ax1.plot(var_phi_trace, label="Var(Δφ)", color="orchid")
ax2 = ax1.twinx()
ax2.plot(entropy_trace, label="spectral entropy", color="seagreen")
ax2.plot(corr_trace, label="corr(Δφ, κ)", color="goldenrod")
ax1.set_xlabel("step")
ax1.set_ylabel("energy / variance")
ax2.set_ylabel("entropy / correlation")
fig.suptitle("G8 — Quantum Decoherence Limit Dynamics")
fig.legend()
plt.tight_layout()
plt.savefig("PAEV_TestG8_DecoherenceTrace.png", dpi=150)

# === FINAL ψ-SPECTRUM ===
psi = theta + 1j * kappa
psi_fft = np.log10(np.abs(fftshift(fft2(psi)))**2 + 1e-8)
plt.figure(figsize=(6,6))
plt.imshow(psi_fft, cmap=cm.magma)
plt.title("G8 — ψ Spectrum (decoherence regime)")
plt.colorbar(label="log₁₀|ψ(k)|²")
plt.savefig("PAEV_TestG8_PsiSpectrum.png", dpi=150)

# === PHASE-CURVATURE COHERENCE MAP ===
plt.figure(figsize=(6,5))
plt.scatter(entropy_trace, corr_trace, s=10, c=np.linspace(0,1,len(corr_trace)), cmap="plasma")
plt.xlabel("spectral entropy")
plt.ylabel("corr(Δφ, κ)")
plt.title("G8 — Phase–Curvature Coherence Portrait")
plt.savefig("PAEV_TestG8_CoherencePortrait.png", dpi=150)

print("✅ Saved files:")
print(" - PAEV_TestG8_DecoherenceTrace.png")
print(" - PAEV_TestG8_PsiSpectrum.png")
print(" - PAEV_TestG8_CoherencePortrait.png")
print("----------------------------------------------------------")