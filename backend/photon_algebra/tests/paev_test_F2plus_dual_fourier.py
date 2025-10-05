# ==========================================================
# Test F2+ — Dual Fourier Diagnostics & Dynamic Spectral Coupling
# ==========================================================
# Purpose:
#   Extend the stability propagation test (F2) with spectral analysis.
#   Detect coherence, mode-locking, and energy exchange in Fourier space.
#
# Outputs:
#   - Animation of θ-field propagation
#   - Dual Fourier power spectra of θ and κ
#   - Cross-spectrum correlation map
#   - Spectral entropy evolution
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# Grid setup
N = 128
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
dx = x[1] - x[0]

# Simulation parameters
steps = 400
dt = 0.01
perturbation_mode = True

# Coefficients (imported from F1 analysis — can be tuned)
c1, c3 = 0.81, 0.14
d1, d2, d3 = 0.04, 0.13, -0.085

# Initialize fields
theta = np.zeros((N, N))
theta_t = np.zeros_like(theta)
kappa = 0.02 * np.random.randn(N, N)

# Inject localized perturbation
if perturbation_mode:
    print("💥 Perturbation mode enabled — injecting Gaussian pulse.")
    r2 = X**2 + Y**2
    theta += np.exp(-r2 / 0.05)

# Utilities
def laplacian(Z):
    return (-4 * Z +
            np.roll(Z, 1, 0) + np.roll(Z, -1, 0) +
            np.roll(Z, 1, 1) + np.roll(Z, -1, 1)) / (dx**2)

def gradient(Z):
    gx = (np.roll(Z, -1, 1) - np.roll(Z, 1, 1)) / (2 * dx)
    gy = (np.roll(Z, -1, 0) - np.roll(Z, 1, 0)) / (2 * dx)
    return gx, gy

# Diagnostics
frames = []
energy_trace = []
corr_trace = []
spectral_entropy_trace = []

# Main evolution loop
for step in range(steps):
    # Compute derivatives
    lap_theta = laplacian(theta)
    grad_theta_x, grad_theta_y = gradient(theta)
    grad_theta2 = grad_theta_x**2 + grad_theta_y**2
    grad_kappa_x, grad_kappa_y = gradient(kappa)
    grad_kappa2 = grad_kappa_x**2 + grad_kappa_y**2

    # Coupled evolution equations
    div_kappa_grad = (
        (np.roll(kappa*grad_theta_x, -1, 1) - np.roll(kappa*grad_theta_x, 1, 1)) +
        (np.roll(kappa*grad_theta_y, -1, 0) - np.roll(kappa*grad_theta_y, 1, 0))
    ) / (2 * dx)

    theta_tt = c1 * lap_theta + c3 * div_kappa_grad
    theta_t += dt * theta_tt
    theta += dt * theta_t

    kappa_dot = d1 * laplacian(kappa) + d2 * grad_theta2 + d3 * kappa
    kappa += dt * kappa_dot

    # Lagrangian density and correlation
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 \
        + 0.04 * kappa**2 - 0.02 * grad_kappa2
    energy_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta * kappa))

    # Fourier analysis
    theta_fft = np.fft.fftshift(np.abs(np.fft.fft2(theta))**2)
    kappa_fft = np.fft.fftshift(np.abs(np.fft.fft2(kappa))**2)

    # Spectral entropy
    p = theta_fft / np.sum(theta_fft)
    S = -np.nansum(p * np.log(p + 1e-12))
    spectral_entropy_trace.append(S)

    # Save frames for animation
    if step % 20 == 0:
        normed = (theta - np.min(theta)) / (np.ptp(theta) + 1e-8)
        frames.append(np.uint8(plt.cm.twilight(normed) * 255))

# === Save outputs ===
imageio.mimsave("PAEV_TestF2Plus_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF2Plus_Propagation.gif")

# Energy evolution
plt.figure()
plt.plot(energy_trace, color='blue')
plt.title("Test F2+ — Mean Lagrangian Evolution")
plt.xlabel("Step")
plt.ylabel("⟨ℒ⟩")
plt.tight_layout()
plt.savefig("PAEV_TestF2Plus_Energy.png")
plt.close()
print("✅ Saved file: PAEV_TestF2Plus_Energy.png")

# Correlation evolution
plt.figure()
plt.plot(corr_trace, color='green')
plt.title("Test F2+ — ⟨θ·κ⟩ Correlation Evolution")
plt.xlabel("Step")
plt.ylabel("⟨θ·κ⟩")
plt.tight_layout()
plt.savefig("PAEV_TestF2Plus_Correlation.png")
plt.close()
print("✅ Saved file: PAEV_TestF2Plus_Correlation.png")

# Spectral entropy trace
plt.figure()
plt.plot(spectral_entropy_trace, color='purple')
plt.title("Test F2+ — Spectral Entropy Evolution")
plt.xlabel("Step")
plt.ylabel("Entropy S")
plt.tight_layout()
plt.savefig("PAEV_TestF2Plus_SpectralEntropy.png")
plt.close()
print("✅ Saved file: PAEV_TestF2Plus_SpectralEntropy.png")

# Final Fourier diagnostics
theta_fft_final = np.fft.fftshift(np.abs(np.fft.fft2(theta))**2)
kappa_fft_final = np.fft.fftshift(np.abs(np.fft.fft2(kappa))**2)
cross_fft = np.real(np.fft.fftshift(np.fft.fft2(theta) * np.conj(np.fft.fft2(kappa))))

plt.figure(figsize=(15,5))
plt.subplot(1,3,1)
plt.imshow(np.log(theta_fft_final + 1e-8), cmap='inferno')
plt.title("θ Spectrum (log power)")
plt.colorbar()

plt.subplot(1,3,2)
plt.imshow(np.log(kappa_fft_final + 1e-8), cmap='magma')
plt.title("κ Spectrum (log power)")
plt.colorbar()

plt.subplot(1,3,3)
plt.imshow(cross_fft, cmap='coolwarm')
plt.title("Cross-Spectral Correlation Re[θ̃·κ̃*]")
plt.colorbar()

plt.tight_layout()
plt.savefig("PAEV_TestF2Plus_DualFourier.png")
plt.close()
print("✅ Saved file: PAEV_TestF2Plus_DualFourier.png")

# Summary
print("\n=== Test F2+ — Dual Fourier Diagnostics Complete ===")
print(f"⟨ℒ⟩ final = {np.nanmean(energy_trace):.4e}")
print(f"⟨θ·κ⟩ final = {np.nanmean(corr_trace):.4e}")
print(f"Spectral entropy (final) = {spectral_entropy_trace[-1]:.4e}")
print(f"Perturbation mode: {'ON' if perturbation_mode else 'OFF'}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")