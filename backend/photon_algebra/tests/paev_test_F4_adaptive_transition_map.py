# ==========================================================
# Test F4 - Adaptive Transition Map
#   Self-adaptive coupling decay and nonlinear damping
#   Detects regime transitions (coherent ↔ decoherent)
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# numerical helpers
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
N = 96
steps = 300
dt = 0.02
dx = 1.0 / N

# base coefficients
c1, c3 = 1.0, 0.6
d1, d2, d3 = 0.25, 0.2, -0.05
mu = 0.1              # cubic curvature damping
chi0 = 0.5            # initial coupling
tau_chi = 80          # decay timescale
perturbation = True

# ----------------------------
# initial fields
# ----------------------------
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

rng = np.random.default_rng(123)
theta = 0.5 * np.exp(-(X**2 + Y**2) / 0.4)
kappa = 0.4 * np.exp(-(X**2 + Y**2) / 0.3)
theta_t = np.zeros_like(theta)

if perturbation:
    print("💥 Perturbation mode enabled - injecting Gaussian pulse.")
    theta += 0.03 * np.exp(-((X**2 + Y**2)/0.1)) * (1 + 0.1 * rng.standard_normal((N,N)))

# ----------------------------
# diagnostics
# ----------------------------
L_trace, corr_trace, entropy_trace = [], [], []
frames = []

def spectral_entropy(field):
    fftmag = np.abs(np.fft.fftshift(np.fft.fft2(field)))**2
    p = fftmag / np.sum(fftmag)
    p = np.where(p > 1e-12, p, 1e-12)
    return -np.sum(p * np.log(p))

# ----------------------------
# main evolution
# ----------------------------
for t in range(steps):
    chi_t = chi0 * np.exp(-t / tau_chi)
    gx, gy = grad_xy(theta)
    grad_theta2 = gx**2 + gy**2
    grad_kx, grad_ky = grad_xy(kappa)
    grad_kappa2 = grad_kx**2 + grad_ky**2
    lap_theta = laplacian(theta)
    lap_kappa = laplacian(kappa)

    # update equations
    div_kappa_grad = (
        (np.roll(kappa*gx, -1, 1) - np.roll(kappa*gx, 1, 1)) +
        (np.roll(kappa*gy, -1, 0) - np.roll(kappa*gy, 1, 0))
    ) / (2 * dx)

    theta_tt = c1 * lap_theta + c3 * div_kappa_grad
    theta_t += dt * theta_tt
    theta += dt * theta_t

    kappa_dot = d1 * lap_kappa + d2 * grad_theta2 + d3 * kappa - mu * kappa**3
    kappa += dt * kappa_dot

    # diagnostics
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 + 0.04 * kappa**2
    L_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta * kappa))
    entropy_trace.append(spectral_entropy(theta))

    # visualization
    if t % 15 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7, 3))
        ax[0].imshow(theta, cmap="plasma")
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
# analysis
# ----------------------------
entropy_trace = np.array(entropy_trace)
L_trace = np.array(L_trace)
corr_trace = np.array(corr_trace)

# detect transition
dE = np.gradient(entropy_trace)
transition_idx = np.argmax(dE > np.mean(dE) + 2 * np.std(dE))
tau_c = np.argmax(entropy_trace < 0.9 * np.max(entropy_trace))

# ----------------------------
# plots
# ----------------------------
plt.figure(figsize=(7, 4))
plt.plot(L_trace, label="⟨L⟩")
plt.plot(corr_trace, label="⟨θ*κ⟩")
plt.plot(entropy_trace / np.max(entropy_trace), label="Spectral entropy (norm.)")
plt.axvline(transition_idx, color="magenta", ls="--", label="transition")
plt.title("F4 - Adaptive Energy, Correlation, and Entropy")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestF4_Adaptive_EnergyTrace.png")
plt.close()
print("✅ Saved file: PAEV_TestF4_Adaptive_EnergyTrace.png")

# phase-space map
plt.figure(figsize=(6, 5))
plt.plot(entropy_trace, corr_trace, color="orange", lw=1.8)
plt.xlabel("Spectral entropy")
plt.ylabel("⟨θ*κ⟩")
plt.title("F4 - Adaptive Phase Trajectory")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_TestF4_Adaptive_PhaseMap.png")
plt.close()
print("✅ Saved file: PAEV_TestF4_Adaptive_PhaseMap.png")

# transition mask
mask = (entropy_trace > np.median(entropy_trace)).astype(float)
plt.figure(figsize=(7, 3))
plt.imshow(mask[np.newaxis, :], cmap="cividis", aspect="auto")
plt.yticks([])
plt.xlabel("Step")
plt.title("F4 - Coherence->Decoherence Transition Map")
plt.tight_layout()
plt.savefig("PAEV_TestF4_Adaptive_TransitionMap.png")
plt.close()
print("✅ Saved file: PAEV_TestF4_Adaptive_TransitionMap.png")

# animation
imageio.mimsave("PAEV_TestF4_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF4_Propagation.gif")

# ----------------------------
# summary
# ----------------------------
print("\n=== Test F4 - Adaptive Transition Map Complete ===")
print(f"⟨L⟩ final = {L_trace[-1]:.4e}")
print(f"⟨θ*κ⟩ final = {corr_trace[-1]:.4e}")
print(f"Spectral entropy final = {entropy_trace[-1]:.4e}")
print(f"Transition detected at step {transition_idx}")
print(f"Estimated coherence lifetime τ_c ≈ {tau_c} steps")
print("Perturbation mode:", "ON" if perturbation else "OFF")
print("\nAll output files saved in working directory.")
print("----------------------------------------------------------")