"""
PAEV Test F8 — Predictive Cosmogenesis (Stabilized)
---------------------------------------------------
Simulates meta-adaptive cosmogenesis dynamics:
inflation, expansion, and reheating phases with bounded field evolution.

Outputs:
 - PAEV_TestF8_Cosmogenesis_Trace.png
 - PAEV_TestF8_ScaleFactor.png
 - PAEV_TestF8_StructureFormation.png
 - PAEV_TestF8_VacuumEnergy_Phase.png
 - PAEV_TestF8_Propagation.gif
 - PAEV_TestF8_Summary.txt
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# === Parameters ===
nx, ny = 80, 80
steps = 320
dt = 0.02
dx = 1.0

# Field coefficients
c1, c2, c3 = 0.8, 0.5, 0.6
G_eff = 0.02  # effective gravitational constant

# Adaptive coupling parameters
chi, alpha = 0.15, 0.05
a, a_dot = 1.0, 0.0  # cosmic scale factor

# --- Initial Gaussian curvature pulse ---
x = np.linspace(-4, 4, nx)
y = np.linspace(-4, 4, ny)
X, Y = np.meshgrid(x, y)
theta = np.exp(-(X**2 + Y**2))
kappa = np.exp(-0.8 * (X**2 + Y**2))
theta_t = np.zeros_like(theta)

print("🌌 Initiating F8 — Predictive Cosmogenesis Mode...")
print("💥 Perturbation mode enabled — injecting Gaussian curvature pulse.")

# === Helper functions ===
def laplacian(Z):
    return (
        -4 * Z +
        np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0) +
        np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1)
    ) / dx**2

def spectral_entropy(field):
    fft_mag = np.abs(np.fft.fft2(field))**2
    fft_mag = np.nan_to_num(fft_mag, nan=0.0, posinf=0.0, neginf=0.0)
    p = fft_mag / np.sum(fft_mag)
    p = np.clip(p, 1e-12, 1)
    return -np.sum(p * np.log(p)) / np.log(p.size)

def gravitational_potential(kappa):
    phi = np.real(np.fft.ifft2(-np.fft.fft2(kappa) / (1 + np.fft.fftfreq(nx)[:, None]**2 + np.fft.fftfreq(ny)[None, :]**2)))
    return np.nan_to_num(phi, nan=0.0, posinf=0.0, neginf=0.0)

# === Storage ===
energy_trace, corr_trace, entropy_trace = [], [], []
a_trace, Lambda_trace, chi_trace, alpha_trace = [], [], [], []

frames = []

# === Main loop ===
for step in range(steps):
    lap_theta = laplacian(theta)
    lap_kappa = laplacian(kappa)
    phi = gravitational_potential(kappa)

    # Gradient energy (bounded)
    grad_theta_x = (np.roll(theta, -1, axis=1) - np.roll(theta, 1, axis=1)) / (2 * dx)
    grad_theta_y = (np.roll(theta, -1, axis=0) - np.roll(theta, 1, axis=0)) / (2 * dx)
    grad_theta2 = np.clip(grad_theta_x**2 + grad_theta_y**2, 0, 1e3)

    grad_phi2 = np.gradient(phi)[0]**2 + np.gradient(phi)[1]**2
    grad_phi2 = np.clip(grad_phi2, 0, 1e3)

    # --- Lagrangian with stability bounds ---
    L = (
        0.5 * np.clip(theta_t**2 - c1 * grad_theta2, -1e3, 1e3)
        - 0.5 * c3 * np.clip(kappa * grad_theta2, -1e3, 1e3)
        + 0.03 * np.clip(kappa**2, 0, 1e3)
        - 0.01 * grad_phi2
    )

    # --- Stable field evolution ---
    theta_tt = np.clip(c1 * lap_theta + chi * lap_kappa - 0.05 * phi, -10, 10)
    kappa_dot = np.clip(c2 * lap_kappa + c3 * grad_theta2 - alpha * kappa + 0.01 * phi, -10, 10)

    theta_t += dt * theta_tt
    theta += dt * theta_t
    kappa += dt * kappa_dot

    theta = np.clip(theta, -5, 5)
    kappa = np.clip(kappa, -5, 5)

    # --- Adaptive dynamics ---
    E_density = np.nanmean(L)
    a_dot += dt * np.clip(E_density * G_eff, -0.05, 0.05)
    a += dt * a_dot

    chi += 0.001 * (np.nanmean(kappa) - 0.5 * np.nanmean(theta)) - 0.0005 * chi
    alpha += 0.001 * (np.nanstd(kappa) - np.nanstd(theta)) - 0.0005 * alpha
    Lambda_t = np.clip(np.nanvar(kappa) * 1e-2, 0, 1e2)
    corr = np.nanmean(theta * kappa)
    entropy = spectral_entropy(theta)

    energy_trace.append(E_density)
    corr_trace.append(corr)
    entropy_trace.append(entropy)
    a_trace.append(a)
    Lambda_trace.append(Lambda_t)
    chi_trace.append(chi)
    alpha_trace.append(alpha)

    # === Frame capture ===
    if step % 20 == 0:
        fig, axs = plt.subplots(1, 2, figsize=(6, 3))
        axs[0].imshow(theta, cmap="inferno")
        axs[0].set_title(f"θ field @ step {step}")
        axs[1].imshow(kappa, cmap="inferno")
        axs[1].set_title("κ field")
        plt.tight_layout()
        fig.canvas.draw()
        frame = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        frame = frame.reshape(fig.canvas.get_width_height()[::-1] + (4,))
        frames.append(frame)
        plt.close(fig)

# === Final Plots ===

# Energy, correlation, entropy, and coupling evolution
plt.figure(figsize=(7, 4))
plt.plot(energy_trace, label="⟨ℒ⟩")
plt.plot(corr_trace, label="⟨θ·κ⟩")
plt.plot(np.array(entropy_trace)/np.max(entropy_trace), label="Spectral entropy (norm.)")
plt.plot(np.array(chi_trace)/np.max(chi_trace), "--", label="χ(t)/χmax")
plt.axvline(0, color="magenta", linestyle="--", label="transition")
plt.legend()
plt.title("F8 — Predictive Cosmogenesis Dynamics")
plt.savefig("PAEV_TestF8_Cosmogenesis_Trace.png")
plt.close()

# Scale factor evolution
plt.figure()
plt.plot(a_trace, color="orange")
plt.title("F8 — Cosmic Scale Factor a(t)")
plt.xlabel("Step")
plt.ylabel("a(t)")
plt.savefig("PAEV_TestF8_ScaleFactor.png")
plt.close()

# Structure formation (final θ vs κ field)
fig, axs = plt.subplots(1, 2, figsize=(6, 3))
axs[0].imshow(theta, cmap="inferno")
axs[0].set_title(f"θ field @ step {steps-1}")
axs[1].imshow(kappa, cmap="inferno")
axs[1].set_title("κ field")
plt.tight_layout()
plt.savefig("PAEV_TestF8_StructureFormation.png")
plt.close()

# Vacuum energy vs expansion rate (inflation→reheating)
plt.figure()
plt.plot(Lambda_trace, a_trace, color="teal")
plt.title("F8 — Vacuum Energy vs Expansion Rate")
plt.xlabel("Λ(t)")
plt.ylabel("a(t)")
plt.grid(True)
plt.savefig("PAEV_TestF8_VacuumEnergy_Phase.png")
plt.close()

# === Save animation ===
import imageio
imageio.mimsave("PAEV_TestF8_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF8_Propagation.gif")

# === Summary output ===
summary = f"""
=== Test F8 — Predictive Cosmogenesis Complete ===
⟨ℒ⟩ final = {energy_trace[-1]:.4e}
⟨θ·κ⟩ final = {corr_trace[-1]:.4e}
Spectral entropy final = {entropy_trace[-1]:.4e}
a(t) final = {a_trace[-1]:.4e}
Λ final = {Lambda_trace[-1]:.4e}
χ final = {chi_trace[-1]:.4e}
α final = {alpha_trace[-1]:.4e}
Perturbation mode: ON

All output files saved in working directory.
----------------------------------------------------------
"""

print(summary)
with open("PAEV_TestF8_Summary.txt", "w") as f:
    f.write(summary)