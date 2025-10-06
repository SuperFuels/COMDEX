# ==========================================================
# Test F5 — Adaptive Feedback Response (Hierarchical Control)
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# helpers
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
# parameters
# ----------------------------
N = 64
steps = 300
dt = 0.02

# base coefficients (from F4)
c1, c3 = 0.8, 0.6
d1, d2, d3 = 0.1, 0.3, -0.02
gamma = 0.02

# adaptive feedback parameters
chi = 0.2           # initial coupling
alpha = 0.05        # adaptation rate
target_entropy = 1.25  # equilibrium entropy target

# initial fields
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
rng = np.random.default_rng(42)

theta = np.exp(-(X**2 + Y**2) / 0.5) + 0.02 * rng.standard_normal((N, N))
theta_t = np.zeros_like(theta)
kappa = np.exp(-(X**2 + Y**2) / 0.4) + 0.02 * rng.standard_normal((N, N))

# traces
energy_trace, corr_trace, entropy_trace, chi_trace = [], [], [], []
frames = []

# ----------------------------
# evolution
# ----------------------------
for t in range(steps):
    lap_theta = laplacian(theta)
    gx, gy = grad_xy(theta)
    grad_theta2 = gx**2 + gy**2

    div_kappa_grad = (
        (np.roll(kappa * gx, -1, 1) - np.roll(kappa * gx, 1, 1)) +
        (np.roll(kappa * gy, -1, 0) - np.roll(kappa * gy, 1, 0))
    ) / 2.0

    theta_tt = c1 * lap_theta + chi * div_kappa_grad - gamma * theta_t
    theta_t += dt * theta_tt
    theta += dt * theta_t

    kappa_dot = d1 * laplacian(kappa) + d2 * grad_theta2 + d3 * kappa
    kappa += dt * kappa_dot

    # compute diagnostics
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 \
        + 0.04 * kappa**2 - 0.02 * (grad_xy(kappa)[0]**2 + grad_xy(kappa)[1]**2)

    # spectral entropy
    fft_theta = np.abs(np.fft.fft2(theta))**2
    p = fft_theta / np.sum(fft_theta)
    p = np.clip(p, 1e-12, None)
    entropy = -np.sum(p * np.log(p))
    entropy /= np.log(p.size)

    # adaptive feedback update
    chi += alpha * (target_entropy - entropy)
    chi = np.clip(chi, 0.05, 0.5)

    # record
    energy_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta * kappa))
    entropy_trace.append(entropy)
    chi_trace.append(chi)

    # visuals
    if t % 30 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7.5, 3.2))
        ax[0].imshow(theta, cmap="inferno")
        ax[0].set_title(f"θ field @ step {t}")
        ax[0].axis("off")
        ax[1].imshow(kappa, cmap="magma")
        ax[1].set_title("κ field")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# transition detection
# ----------------------------
transition_step = np.argmax(np.gradient(entropy_trace) > 0.01)
if transition_step == 0:
    transition_step = 0

# ----------------------------
# plots
# ----------------------------
# 1. Energy, correlation, entropy, chi evolution
plt.figure(figsize=(7, 4))
plt.plot(energy_trace, label="⟨ℒ⟩")
plt.plot(corr_trace, label="⟨θ·κ⟩")
plt.plot(entropy_trace, label="Spectral entropy (norm.)")
plt.plot(np.array(chi_trace)/max(chi_trace), label="χ(t) / χₘₐₓ", linestyle="--")
plt.axvline(transition_step, color="magenta", linestyle="--", label="transition")
plt.legend()
plt.title("F5 — Adaptive Feedback Response")
plt.tight_layout()
plt.savefig("PAEV_TestF5_AdaptiveFeedback_Trace.png")
plt.close()
print("✅ Saved file: PAEV_TestF5_AdaptiveFeedback_Trace.png")

# 2. Phase portrait: correlation vs entropy
plt.figure(figsize=(5.5, 4))
plt.plot(entropy_trace, corr_trace, color="orange")
plt.xlabel("Spectral entropy")
plt.ylabel("⟨θ·κ⟩")
plt.title("F5 — Phase Portrait (Adaptive Coherence)")
plt.tight_layout()
plt.savefig("PAEV_TestF5_AdaptiveFeedback_PhasePortrait.png")
plt.close()
print("✅ Saved file: PAEV_TestF5_AdaptiveFeedback_PhasePortrait.png")

# 3. Animation
imageio.mimsave("PAEV_TestF5_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF5_Propagation.gif")

# ----------------------------
# summary
# ----------------------------
summary = f"""
=== Test F5 — Adaptive Feedback Response (Hierarchical Control) ===
⟨ℒ⟩ final = {energy_trace[-1]:.4e}
⟨θ·κ⟩ final = {corr_trace[-1]:.4e}
Spectral entropy final = {entropy_trace[-1]:.4e}
Adaptive coupling χ final = {chi_trace[-1]:.4e}
Transition detected at step {transition_step}
Perturbation mode: ON

All output files saved in working directory.
----------------------------------------------------------
"""
print(summary)

with open("PAEV_TestF5_AdaptiveFeedback_Summary.txt", "w") as f:
    f.write(summary)