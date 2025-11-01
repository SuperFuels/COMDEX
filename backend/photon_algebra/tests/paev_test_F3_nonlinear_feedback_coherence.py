# ==========================================================
# Test F3 - Nonlinear Feedback & Coherence Lifetime
#   Explore nonlinear curvature feedback, decoherence, and
#   dynamic stability using θ-κ coupled propagation.
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# Numerics & utilities
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

def spectral_entropy(field):
    F = np.abs(np.fft.fftshift(np.fft.fft2(field))) ** 2
    P = F / np.sum(F)
    P = P[P > 0]
    return -np.sum(P * np.log(P + 1e-12))

def autocorr_decay(signal, max_lag=200):
    """Estimate temporal coherence lifetime τ_c"""
    signal = (signal - np.mean(signal)) / (np.std(signal) + 1e-9)
    ac = np.correlate(signal, signal, mode='full')
    ac = ac[len(ac)//2:]
    ac /= ac[0]
    # find first crossing below 1/e
    below = np.where(ac < np.exp(-1))[0]
    return below[0] if len(below) > 0 else len(ac)

# ----------------------------
# Parameters
# ----------------------------
N = 64
steps = 250
dt = 0.02

# Physical constants (moderate-nonlinear regime)
c1 = 0.8      # wave coupling
c3 = 0.3      # curvature-phase coupling
chi = 0.35    # nonlinear feedback
gamma = 0.015 # mild damping
eta = 0.05    # curvature relaxation
zeta = 0.03   # curvature diffusion
perturb = True

# ----------------------------
# Initial fields
# ----------------------------
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
rng = np.random.default_rng(42)

theta = 0.4 * np.exp(-(X**2 + Y**2) / 0.5)
theta_t = np.zeros_like(theta)
kappa = 0.08 * np.exp(-(X**2 + Y**2) / 0.3)

if perturb:
    print("💥 Perturbation mode enabled - injecting Gaussian pulse.")
    theta += 0.05 * np.exp(-((X-0.3)**2 + (Y+0.2)**2) / 0.1)
    kappa += 0.02 * np.exp(-((X+0.2)**2 + (Y-0.1)**2) / 0.1)

# ----------------------------
# Diagnostics
# ----------------------------
energy_trace = []
corr_trace = []
entropy_trace = []
frames = []

# ----------------------------
# Main propagation loop
# ----------------------------
for t in range(steps):
    lap_theta = laplacian(theta)
    grad_theta_x, grad_theta_y = grad_xy(theta)
    grad_theta2 = grad_theta_x**2 + grad_theta_y**2
    lap_kappa = laplacian(kappa)

    # Nonlinear feedback term
    nonlinear_term = chi * (kappa**2) * lap_theta

    # Wave equation with nonlinear curvature feedback
    theta_tt = c1 * lap_theta + c3 * laplacian(kappa * grad_theta2) + nonlinear_term - gamma * theta_t
    theta_t += dt * theta_tt
    theta += dt * theta_t

    # Curvature evolution
    kappa_dot = zeta * lap_kappa - eta * kappa + 0.2 * grad_theta2
    kappa += dt * kappa_dot

    # Diagnostics
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 - 0.05 * kappa**2
    energy_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta * kappa))
    entropy_trace.append(spectral_entropy(theta))

    # Snapshot frames
    if t % 15 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.2))
        ax[0].imshow(theta, cmap="twilight", vmin=-1, vmax=1)
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
# Coherence & transition detection
# ----------------------------
tau_c = autocorr_decay(corr_trace)
transition_step = np.argmax(np.gradient(entropy_trace) > 0.05 * np.max(np.gradient(entropy_trace)))

# ----------------------------
# Plots & output
# ----------------------------
# Energy / correlation / entropy evolution
plt.figure(figsize=(7,4))
plt.plot(energy_trace, label="⟨L⟩")
plt.plot(corr_trace, label="⟨θ*κ⟩")
plt.plot(entropy_trace, label="Spectral entropy")
plt.axvline(transition_step, color='magenta', ls='--', lw=1.2, label="transition")
plt.legend()
plt.title("F3 - Energy, Correlation, and Entropy Evolution")
plt.tight_layout()
plt.savefig("PAEV_TestF3_Coherence_Trace.png")
plt.close()
print("✅ Saved file: PAEV_TestF3_Coherence_Trace.png")

# Entropy-lifetime overlay
plt.figure(figsize=(6,4))
plt.plot(entropy_trace, label="Spectral entropy", color="orange")
plt.axhline(np.mean(entropy_trace), color="gray", ls="--", lw=1)
plt.text(0.7*steps, np.mean(entropy_trace)+0.05, f"τ_c ≈ {tau_c} steps", color="blue")
plt.xlabel("Step")
plt.ylabel("Entropy / τ_c")
plt.title("F3 - Entropy & Coherence Lifetime")
plt.tight_layout()
plt.savefig("PAEV_TestF3_Entropy_Coherence.png")
plt.close()
print("✅ Saved file: PAEV_TestF3_Entropy_Coherence.png")

# Animation
imageio.mimsave("PAEV_TestF3_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF3_Propagation.gif")

# ----------------------------
# Summary
# ----------------------------
summary = f"""
=== Test F3 - Nonlinear Feedback & Coherence Lifetime ===
⟨L⟩ final = {energy_trace[-1]:.4e}
⟨θ*κ⟩ final = {corr_trace[-1]:.4e}
Spectral entropy final = {entropy_trace[-1]:.4e}
Estimated coherence lifetime τ_c ≈ {tau_c} steps
Transition detected at step {transition_step}
Perturbation mode: {'ON' if perturb else 'OFF'}

All output files saved in working directory.
----------------------------------------------------------
"""

print(summary)
with open("PAEV_TestF3_Summary.txt", "w") as f:
    f.write(summary)