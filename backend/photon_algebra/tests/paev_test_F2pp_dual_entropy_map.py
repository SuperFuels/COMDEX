# ==========================================================
# Test F2++ - Dual-Fourier + Entropy Map + Spectral Centroid
#   Tracks Fourier-space evolution and entropy in time
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from scipy.fft import fft2, fftshift

# ----------------------------
# numerics & helpers
# ----------------------------
def laplacian(Z):
    return (
        -4.0 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

def grad_xy(Z):
    gx = 0.5 * (np.roll(Z, -1, 1) - np.roll(Z, 1, 1))
    gy = 0.5 * (np.roll(Z, -1, 0) - np.roll(Z, 1, 0))
    return gx, gy

# ----------------------------
# parameters (stable defaults)
# ----------------------------
N = 64
steps = 180
dt = 0.015
perturb_mode = True

c1, c3 = 0.4, 0.15
d1, d2, d3 = 0.2, 0.1, -0.05
noise_amp = 5e-4

x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# ----------------------------
# initial fields
# ----------------------------
rng = np.random.default_rng(42)
theta = np.exp(-(X**2 + Y**2) / 0.4)
kappa = np.exp(-(X**2 + Y**2) / 0.5)

if perturb_mode:
    print("💥 Perturbation mode enabled - injecting Gaussian pulse.")
    theta += 0.05 * np.exp(-(X**2 + Y**2) / 0.1)
    kappa += 0.02 * rng.standard_normal((N, N))

theta_t = np.zeros_like(theta)

# ----------------------------
# diagnostics storage
# ----------------------------
energy_trace, corr_trace, entropy_trace = [], [], []
spec_centroid_trace = []
frames = []
entropy_map = []

# ----------------------------
# main loop
# ----------------------------
for t in range(steps):
    gx, gy = grad_xy(theta)
    grad_theta2 = gx**2 + gy**2

    # PDE updates (stabilized with tanh limiter)
    lap_theta = laplacian(theta)
    lap_kappa = laplacian(kappa)
    div_kappa_grad = (
        (np.roll(kappa * gx, -1, 1) - np.roll(kappa * gx, 1, 1))
        + (np.roll(kappa * gy, -1, 0) - np.roll(kappa * gy, 1, 0))
    ) * 0.5
    theta_tt = c1 * lap_theta + c3 * div_kappa_grad
    theta_t += dt * theta_tt
    theta += dt * theta_t

    kappa_dot = d1 * lap_kappa + d2 * grad_theta2 + d3 * kappa
    kappa += dt * np.tanh(kappa_dot) + noise_amp * rng.standard_normal((N, N))

    # Lagrangian density (stabilized)
    grad_kappa_x, grad_kappa_y = grad_xy(kappa)
    grad_kappa2 = grad_kappa_x**2 + grad_kappa_y**2
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 \
        + 0.04 * kappa**2 - 0.02 * grad_kappa2
    energy_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta * kappa))

    # Fourier spectrum diagnostics
    theta_fft = fftshift(np.abs(fft2(theta))**2)
    theta_fft /= np.sum(theta_fft) + 1e-12
    entropy = -np.sum(theta_fft * np.log(theta_fft + 1e-12))
    entropy_trace.append(entropy)

    # spectral centroid (energy-weighted mean wavenumber)
    k_indices = np.arange(N)
    spec_centroid = np.sum(k_indices[:, None] * np.sum(theta_fft, axis=1)) / (np.sum(theta_fft) + 1e-12)
    spec_centroid_trace.append(spec_centroid)

    # store 1D radial slice of log-spectrum
    entropy_map.append(np.log10(np.mean(theta_fft, axis=0) + 1e-10))

    # visualization frame
    if t % 15 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7.5, 3.3))
        ax[0].imshow(theta, cmap="magma")
        ax[0].set_title(f"θ @ step {t}")
        ax[0].axis("off")
        ax[1].imshow(kappa, cmap="plasma")
        ax[1].set_title("κ curvature")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# entropy-frequency map
# ----------------------------
entropy_map = np.array(entropy_map).T
plt.figure(figsize=(7, 4))
plt.imshow(entropy_map, aspect='auto', origin='lower', cmap='inferno')
plt.colorbar(label=r'$\log_{10}|\theta(k)|^2$')
plt.xlabel("time step")
plt.ylabel("k (wavenumber index)")
plt.title("Entropy-Frequency Evolution (θ field)")
plt.tight_layout()
plt.savefig("PAEV_TestF2pp_EntropyMap.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF2pp_EntropyMap.png")

# ----------------------------
# spectral centroid trajectory
# ----------------------------
plt.figure(figsize=(6, 4))
plt.plot(spec_centroid_trace, lw=2)
plt.xlabel("time step")
plt.ylabel("spectral centroid ⟨k⟩")
plt.title("Spectral Centroid Trajectory (θ field)")
plt.tight_layout()
plt.savefig("PAEV_TestF2pp_SpectralCentroid.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF2pp_SpectralCentroid.png")

# ----------------------------
# animation
# ----------------------------
imageio.mimsave("PAEV_TestF2pp_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF2pp_Propagation.gif")

# ----------------------------
# summary
# ----------------------------
L_final = energy_trace[-1]
corr_final = corr_trace[-1]
entropy_final = entropy_trace[-1]
print("\n=== Test F2++ - Dual-Fourier + Entropy Map Complete ===")
print(f"⟨L⟩ final = {L_final:.4e}")
print(f"⟨θ*κ⟩ final = {corr_final:.4e}")
print(f"Spectral entropy final = {entropy_final:.4e}")
if np.argmax(np.gradient(entropy_trace)) < len(entropy_trace) // 2:
    print(f"🌀 Transition detected at step {np.argmax(np.gradient(entropy_trace))} (entropy surge).")
print("Perturbation mode:", "ON" if perturb_mode else "OFF")
print("\nAll output files saved in working directory.")
print("----------------------------------------------------------")