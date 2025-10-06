# ==========================================================
# Test F2 — Stability & Propagation (Effective Lagrangian Dynamics)
# ==========================================================
# Purpose:
#   Propagate the θ–κ system using extracted PDE coefficients
#   from Test F1, testing the dynamic stability of the Lagrangian.
#   Optionally injects a Gaussian perturbation and tracks soliton
#   or dissipative wave behavior.
#
# Outputs:
#   - Animated θ, κ fields over time
#   - Lagrangian density map
#   - Energy (⟨ℒ⟩) evolution
#   - θ–κ correlation trace
#   - Fourier spectrum of κ(t)
#
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------------------------------------
# Parameters and coefficients (from Test F1)
# ----------------------------------------------------------
c1, c3 = 0.81037, 0.13982
d1, d2, d3 = 0.03920, 0.12792, -0.08513

N = 200
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
dx = x[1] - x[0]
dt = 0.001
steps = 400
perturbation_mode = True

# ----------------------------------------------------------
# Initial conditions
# ----------------------------------------------------------
theta = np.zeros((N, N))
theta_t = np.zeros_like(theta)
kappa = 0.01 * np.random.randn(N, N)

if perturbation_mode:
    print("💥 Perturbation mode enabled — injecting Gaussian pulse.")
    pulse = np.exp(-((X**2 + Y**2) / 0.1))
    theta += 0.1 * pulse
    kappa += 0.05 * pulse

# ----------------------------------------------------------
# Utility functions
# ----------------------------------------------------------
def laplacian(Z):
    return (
        -4*Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    ) / (dx**2)

def grad(Z):
    return np.gradient(Z, dx, edge_order=2)

# ----------------------------------------------------------
# Simulation arrays
# ----------------------------------------------------------
frames = []
energy_trace = []
corr_trace = []

# ----------------------------------------------------------
# Time evolution loop
# ----------------------------------------------------------
for step in range(steps):
    grad_theta_x, grad_theta_y = grad(theta)
    grad_kappa_x, grad_kappa_y = grad(kappa)
    grad_theta2 = grad_theta_x**2 + grad_theta_y**2
    grad_kappa2 = grad_kappa_x**2 + grad_kappa_y**2

    div_kappa_grad = (
        (np.roll(kappa*grad_theta_x, -1, 1) - np.roll(kappa*grad_theta_x, 1, 1)) +
        (np.roll(kappa*grad_theta_y, -1, 0) - np.roll(kappa*grad_theta_y, 1, 0))
    ) / (2*dx)

    lap_theta = laplacian(theta)
    theta_tt = c1 * lap_theta + c3 * div_kappa_grad
    theta_t += dt * theta_tt
    theta += dt * theta_t

    kappa_dot = d1 * laplacian(kappa) + d2 * grad_theta2 + d3 * kappa
    kappa += dt * kappa_dot

    # Lagrangian density ℒ(x,y)
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 \
        + 0.04 * kappa**2 - 0.02 * grad_kappa2

    energy_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta * kappa))

    if step % 20 == 0:
        frame = np.uint8(plt.cm.plasma((kappa - np.min(kappa)) / (np.ptp(kappa) + 1e-8)) * 255)
        frames.append(frame)

# ----------------------------------------------------------
# Save animation
# ----------------------------------------------------------
imageio.mimsave("PAEV_TestF2_Propagation.gif", frames, fps=15)
print("✅ Saved animation to: PAEV_TestF2_Propagation.gif")

# ----------------------------------------------------------
# Energy plot
# ----------------------------------------------------------
plt.figure()
plt.plot(energy_trace, color="blue")
plt.title("Test F2 — Energy Evolution (Lagrangian Stability)")
plt.xlabel("Time step")
plt.ylabel("Mean Lagrangian ⟨ℒ⟩")
plt.tight_layout()
plt.savefig("PAEV_TestF2_Energy.png")
plt.close()
print("✅ Saved file: PAEV_TestF2_Energy.png")

# ----------------------------------------------------------
# Correlation plot
# ----------------------------------------------------------
plt.figure()
plt.plot(corr_trace, color="purple")
plt.title("Test F2 — Phase–Curvature Correlation Evolution")
plt.xlabel("Time step")
plt.ylabel("⟨θ·κ⟩ correlation")
plt.tight_layout()
plt.savefig("PAEV_TestF2_Correlation.png")
plt.close()
print("✅ Saved file: PAEV_TestF2_Correlation.png")

# ----------------------------------------------------------
# Lagrangian Density Map
# ----------------------------------------------------------
plt.figure(figsize=(6,6))
plt.imshow(L, cmap="inferno", extent=[-1,1,-1,1])
plt.colorbar(label="ℒ value")
plt.title(f"Test F2 — Lagrangian Density ⟨ℒ⟩={np.nanmean(L):.2e}")
plt.tight_layout()
plt.savefig("PAEV_TestF2_Lagrangian.png")
plt.close()
print("✅ Saved file: PAEV_TestF2_Lagrangian.png")

# ----------------------------------------------------------
# Fourier diagnostic — spectral structure of κ field
# ----------------------------------------------------------
fft_spectrum = np.fft.fftshift(np.abs(np.fft.fft2(kappa))**2)
plt.figure(figsize=(6,6))
plt.imshow(np.log(fft_spectrum + 1e-8), cmap="magma", extent=[-1,1,-1,1])
plt.colorbar(label="log |κ(k)|²")
plt.title("Test F2 — Fourier Spectrum of κ Field (log power)")
plt.tight_layout()
plt.savefig("PAEV_TestF2_FourierSpectrum.png")
plt.close()
print("✅ Saved file: PAEV_TestF2_FourierSpectrum.png")

# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------
print("\n=== Test F2 — Stability & Propagation Complete ===")
print(f"⟨ℒ⟩ final = {np.nanmean(L):.4e}")
print(f"⟨θ·κ⟩ final = {np.nanmean(corr_trace):.4e}")
print(f"Perturbation mode: {'ON' if perturbation_mode else 'OFF'}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")