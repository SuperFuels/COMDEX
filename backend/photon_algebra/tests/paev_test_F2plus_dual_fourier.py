# ==========================================================
# Test F2++ - Stabilized Dual-Fourier + Time-Frequency Entropy Map
# ==========================================================
import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from matplotlib.colors import LogNorm

# -------------------------------------
# Core numerics
# -------------------------------------
def laplacian(Z):
    return (-4 * Z
            + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
            + np.roll(Z, 1, 1) + np.roll(Z, -1, 1))

def grad_xy(Z):
    gx = 0.5 * (np.roll(Z, -1, 1) - np.roll(Z, 1, 1))
    gy = 0.5 * (np.roll(Z, -1, 0) - np.roll(Z, 1, 0))
    return gx, gy

def spectral_entropy(field_fft):
    p = np.abs(field_fft)**2
    p /= np.sum(p) + 1e-12
    return -np.sum(p * np.log(p + 1e-12))

# -------------------------------------
# Simulation parameters
# -------------------------------------
N, steps, dt = 64, 180, 0.02
c, gamma, eta, chi, zeta = 0.9, 0.03, 0.05, 0.15, 0.04
noise_amp = 5e-4

x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
rng = np.random.default_rng(42)

theta = 0.3 * np.exp(-(X**2 + Y**2) / 0.5) + 0.05 * rng.standard_normal((N, N))
theta_t = np.zeros_like(theta)
kappa = 0.05 * np.exp(-(X**2 + Y**2) / 0.4) + 0.02 * rng.standard_normal((N, N))

frames, energy_trace, corr_trace, entropy_trace = [], [], [], []
entropy_spectrum = []

print("💥 Perturbation mode enabled - injecting Gaussian pulse.")

# -------------------------------------
# Time evolution
# -------------------------------------
for t in range(steps):
    gx, gy = grad_xy(theta)
    grad_theta2 = np.clip(gx**2 + gy**2, 0, 1e4)
    lap_th = laplacian(theta)

    grad_kx, grad_ky = grad_xy(kappa)
    grad_kappa2 = np.clip(grad_kx**2 + grad_ky**2, 0, 1e4)

    # coupling flux term
    Jx, Jy = kappa * gx, kappa * gy
    div_J = 0.5 * ((np.roll(Jx, -1, 1) - np.roll(Jx, 1, 1)) +
                   (np.roll(Jy, -1, 0) - np.roll(Jy, 1, 0)))

    # adaptive damping + limiter
    gamma_eff = gamma * (1.0 + 0.3 * np.mean(np.abs(theta_t)))
    limiter = 1.0 / (1.0 + 5.0 * np.mean(theta_t**2 + kappa**2))

    # PDE updates (stabilized)
    theta_tt = (c**2) * lap_th - gamma_eff * theta_t + chi * div_J
    theta_t += dt * theta_tt * limiter
    theta += dt * theta_t * limiter

    kappa_dot = zeta * laplacian(kappa) - eta * kappa + chi * (grad_theta2 - np.mean(grad_theta2))
    kappa_dot += noise_amp * rng.standard_normal((N, N))
    kappa += dt * kappa_dot * limiter

    # normalization to prevent runaway
    if t % 10 == 0:
        theta /= (np.std(theta) + 1e-8)
        kappa /= (np.std(kappa) + 1e-8)

    # effective Lagrangian density
    L = 0.5 * (theta_t**2 - c**2 * grad_theta2) - 0.5 * chi * kappa * grad_theta2 \
        + 0.04 * kappa**2 - 0.02 * grad_kappa2

    energy_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta * kappa))

    # spectral diagnostics
    theta_fft = np.fft.fftshift(np.fft.fft2(theta))
    theta_spec = np.abs(theta_fft)**2
    entropy_trace.append(spectral_entropy(theta_fft))
    entropy_spectrum.append(np.log(theta_spec.mean(axis=0) + 1e-10))

    # visual frame
    if t % 15 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7.5, 3.3))
        ax[0].imshow(theta, cmap="twilight", vmin=-np.pi, vmax=np.pi)
        ax[0].set_title(f"θ @ step {t}")
        ax[0].axis("off")
        ax[1].imshow(kappa, cmap="magma")
        ax[1].set_title("κ curvature")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# -------------------------------------
# Save diagnostics
# -------------------------------------
imageio.mimsave("PAEV_TestF2pp_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF2pp_Propagation.gif")

plt.figure(figsize=(6,4))
plt.plot(energy_trace, label="⟨L⟩")
plt.plot(corr_trace, label="⟨θ*κ⟩")
plt.xlabel("step")
plt.legend()
plt.title("F2++ - Energy & Correlation")
plt.tight_layout()
plt.savefig("PAEV_TestF2pp_EnergyCorrelation.png")
plt.close()

plt.figure(figsize=(6,4))
plt.plot(entropy_trace, color="green")
plt.title("F2++ - Spectral Entropy Evolution")
plt.xlabel("time step")
plt.ylabel("S")
plt.tight_layout()
plt.savefig("PAEV_TestF2pp_SpectralEntropy.png")
plt.close()

theta_fft_final = np.abs(np.fft.fftshift(np.fft.fft2(theta)))**2
plt.figure(figsize=(5,4))
plt.imshow(theta_fft_final + 1e-8, norm=LogNorm(), cmap="plasma")
plt.title("F2++ - Final Fourier Spectrum")
plt.colorbar(label="Power")
plt.tight_layout()
plt.savefig("PAEV_TestF2pp_DualFourier.png")
plt.close()

entropy_spectrum = np.array(entropy_spectrum)
plt.figure(figsize=(7,4))
plt.imshow(entropy_spectrum.T, aspect="auto", cmap="inferno", origin="lower")
plt.xlabel("time step")
plt.ylabel("wavenumber index")
plt.title("F2++ - Time-Frequency Entropy Map")
plt.colorbar(label="log ⟨|θ(k,t)|2⟩")
plt.tight_layout()
plt.savefig("PAEV_TestF2pp_TimeFrequencyEntropyMap.png")
plt.close()

# -------------------------------------
# Summary
# -------------------------------------
L_final = np.nanmean(L)
corr_final = np.nanmean(theta * kappa)
entropy_final = entropy_trace[-1]

print("\n=== Test F2++ - Dual-Fourier + Entropy Map Complete ===")
print(f"⟨L⟩ final = {L_final:.4e}")
print(f"⟨θ*κ⟩ final = {corr_final:.4e}")
print(f"Spectral entropy final = {entropy_final:.4e}")
print("Perturbation mode: ON")
print("All output files saved in working directory.")
print("----------------------------------------------------------")