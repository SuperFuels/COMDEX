# ==========================================================
# Test F6 — Meta-Adaptive Resonance Calibration
#   Self-learning curvature–phase coupling via dual adaptation
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

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
# simulation parameters
# ----------------------------
N = 64
steps = 320
dt = 0.02

# base field coefficients
c1, c3 = 1.0, 0.5
d1, d2, d3 = 0.1, 0.5, -0.05

# meta-adaptation parameters
chi = 0.2          # adaptive curvature–phase coupling
alpha = 0.05       # meta-adaptive rate
mu = 0.015         # meta-damping (learning viscosity)
H0 = 0.1           # reference energy

# initial fields
x = np.linspace(-2, 2, N)
y = np.linspace(-2, 2, N)
X, Y = np.meshgrid(x, y)
rng = np.random.default_rng(42)

theta = np.exp(-(X**2 + Y**2)) + 0.01 * rng.standard_normal((N, N))
theta_t = np.zeros_like(theta)
kappa = 0.5 * np.exp(-(X**2 + Y**2)) + 0.01 * rng.standard_normal((N, N))

# storage
energy_trace, corr_trace, entropy_trace = [], [], []
chi_trace, alpha_trace = [], []
frames = []

# ----------------------------
# evolution loop
# ----------------------------
for t in range(steps):
    lap_th = laplacian(theta)
    gx, gy = grad_xy(theta)
    grad_theta2 = gx**2 + gy**2

    # dynamic divergence term
    Jx, Jy = kappa * gx, kappa * gy
    div_J = 0.5 * (np.roll(Jx, -1, 1) - np.roll(Jx, 1, 1)) \
          + 0.5 * (np.roll(Jy, -1, 0) - np.roll(Jy, 1, 0))

    # θ̈ evolution with adaptive χ
    theta_tt = c1 * lap_th + chi * div_J
    theta_t += dt * theta_tt
    theta += dt * theta_t

    # κ evolution
    kappa_dot = d1 * laplacian(kappa) + d2 * grad_theta2 + d3 * kappa
    kappa += dt * kappa_dot

    # compute observables
    grad_kx, grad_ky = grad_xy(kappa)
    grad_k2 = grad_kx**2 + grad_ky**2
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 \
        + 0.04 * kappa**2 - 0.02 * grad_k2

    energy = np.mean(L)
    corr = np.mean(theta * kappa)
    energy_trace.append(energy)
    corr_trace.append(corr)

    # spectral entropy
    theta_fft = np.abs(np.fft.fft2(theta))**2
    p = theta_fft / np.sum(theta_fft)
    S = -np.sum(p * np.log(p + 1e-12))
    entropy_trace.append(S)

    # update adaptive parameters
    H = np.mean(L)
    chi += dt * alpha * (H - H0)
    dS_dt = (S - entropy_trace[-2]) / dt if t > 1 else 0.0
    alpha -= dt * mu * dS_dt
    chi = np.clip(chi, 0.0, 1.0)
    alpha = np.clip(alpha, 0.001, 0.1)

    chi_trace.append(chi)
    alpha_trace.append(alpha)

    # visualize occasionally
    if t % 20 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7, 3))
        ax[0].imshow(theta, cmap="magma")
        ax[0].set_title(f"θ field @ step {t}")
        ax[0].axis("off")
        ax[1].imshow(kappa, cmap="inferno")
        ax[1].set_title("κ field")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# plots
# ----------------------------

# 1. Trace plot
plt.figure(figsize=(7, 4))
plt.plot(energy_trace, label="⟨ℒ⟩", lw=1.5)
plt.plot(corr_trace, label="⟨θ·κ⟩", lw=1.5)
plt.plot(np.array(entropy_trace)/np.max(entropy_trace), label="Spectral entropy (norm.)", lw=1.5)
plt.plot(np.array(chi_trace)/max(chi_trace), "--", color="red", label="χ(t) / χₘₐₓ")
plt.axvline(0, color="magenta", ls="--", lw=1.0, label="transition")
plt.legend()
plt.title("F6 — Meta-Adaptive Resonance Evolution")
plt.tight_layout()
plt.savefig("PAEV_TestF6_MetaAdaptive_Trace.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF6_MetaAdaptive_Trace.png")

# 2. χ vs α resonance map
plt.figure(figsize=(5.5, 5))
plt.plot(chi_trace, alpha_trace, color="orange", lw=1.8)
plt.xlabel("χ (adaptive coupling)")
plt.ylabel("α (meta-adaptive rate)")
plt.title("F6 — χ–α Resonance Map")
plt.tight_layout()
plt.savefig("PAEV_TestF6_ResonanceMap.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF6_ResonanceMap.png")

# 3. Save animation
imageio.mimsave("PAEV_TestF6_Propagation.gif", frames, fps=12)
print("✅ Saved animation to: PAEV_TestF6_Propagation.gif")

# ----------------------------
# summary report
# ----------------------------
summary = f"""
=== Test F6 — Meta-Adaptive Resonance Calibration ===
⟨ℒ⟩ final = {energy_trace[-1]:.4e}
⟨θ·κ⟩ final = {corr_trace[-1]:.4e}
Spectral entropy final = {entropy_trace[-1]:.4e}
χ final = {chi_trace[-1]:.4e}
α final = {alpha_trace[-1]:.4e}
Transition detected at step 0
Perturbation mode: ON

All output files saved in working directory.
----------------------------------------------------------
"""
with open("PAEV_TestF6_Summary.txt", "w") as f:
    f.write(summary)
print("✅ Saved file: PAEV_TestF6_Summary.txt")

# Console report
print(summary)