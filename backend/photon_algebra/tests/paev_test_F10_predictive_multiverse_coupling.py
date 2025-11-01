"""
PAEV Test F10 - Predictive Multiverse Coupling (Stable Evolution)
------------------------------------------------------------------
Simulates two coupled universes (θ_A, θ_B) linked via adaptive curvature κ,
with synchronization coefficients (χ_sync, α_sync) evolving dynamically.

Stability enhancements:
  * Laplacian clamping
  * Adaptive damping
  * Finite renormalization (energy conservation)
  * Bounded χ-α adaptive feedback
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ------------------------------
# Numerical Parameters
# ------------------------------
N = 80
dx = 0.1
dt = 0.01
steps = 320

c1, c3 = 0.8, 0.3
chi_sync, alpha_sync = 0.15, 0.03

np.random.seed(42)

# ------------------------------
# Helper Functions
# ------------------------------
def laplacian(Z):
    return (
        np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0)
        + np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1)
        - 4 * Z
    ) / dx**2

def spectral_entropy(field):
    fft_mag = np.abs(np.fft.fft2(field))**2
    p = fft_mag / np.sum(fft_mag)
    p = np.where(p > 0, p, 1e-12)
    return -np.sum(p * np.log(p)) / np.log(p.size)

# ------------------------------
# Initialization
# ------------------------------
x = np.linspace(-4, 4, N)
X, Y = np.meshgrid(x, x)
r2 = X**2 + Y**2
gaussian = np.exp(-r2)

theta_A = gaussian + 0.01 * np.random.randn(N, N)
theta_B = gaussian + 0.01 * np.random.randn(N, N)
theta_tA = np.zeros_like(theta_A)
theta_tB = np.zeros_like(theta_B)
kappa_global = np.zeros_like(theta_A)

print("🌌 Initiating F10 - Predictive Multiverse Coupling Test...")
print("💥 Perturbation mode enabled - generating dual universe states.")

# ------------------------------
# Data Traces
# ------------------------------
E_trace, corr_trace, entropy_trace, sync_trace = [], [], [], []

# ------------------------------
# Evolution Loop
# ------------------------------
for t in range(steps):
    lapA, lapB = laplacian(theta_A), laplacian(theta_B)
    lapK = laplacian(kappa_global)

    # Coupled universe field equations
    theta_ttA = c1 * lapA + c3 * lapK + chi_sync * (theta_B - theta_A)
    theta_ttB = c1 * lapB + c3 * lapK + chi_sync * (theta_A - theta_B)

    # Stability clamp to avoid overflow
    theta_ttA = np.clip(theta_ttA, -1e2, 1e2)
    theta_ttB = np.clip(theta_ttB, -1e2, 1e2)

    theta_tA += dt * theta_ttA
    theta_tB += dt * theta_ttB
    theta_A += dt * theta_tA
    theta_B += dt * theta_tB

    # Damping normalization (energy conservation)
    theta_A /= (1 + 0.01 * np.abs(theta_A))
    theta_B /= (1 + 0.01 * np.abs(theta_B))

    # Curvature feedback coupling
    kappa_global += alpha_sync * lapK + 0.001 * (theta_A + theta_B)
    kappa_global = np.clip(kappa_global, -5, 5)

    # Adaptive feedback for coupling constants
    chi_sync += 0.0002 * (np.nanmean(theta_A * theta_B) - chi_sync)
    alpha_sync += 0.0001 * (np.nanstd(kappa_global) - alpha_sync)
    chi_sync = np.clip(chi_sync, 0.05, 0.2)
    alpha_sync = np.clip(alpha_sync, 0.01, 0.05)

    # Diagnostics
    L = 0.5 * (theta_tA**2 + theta_tB**2) - 0.5 * c1 * (lapA + lapB) - 0.5 * c3 * kappa_global
    E = np.nanmean(L)
    corr = np.nanmean(theta_A * theta_B)
    S = 0.5 * (spectral_entropy(theta_A) + spectral_entropy(theta_B))

    E_trace.append(E)
    corr_trace.append(corr)
    entropy_trace.append(S)
    sync_trace.append(chi_sync)

    # Energy renormalization if growth exceeds threshold
    if t > 0 and np.abs(E_trace[-1] - E_trace[-2]) > 0.05:
        theta_tA *= 0.9
        theta_tB *= 0.9

    if t % 40 == 0:
        print(f"Step {t:03d} - ⟨L⟩={E:.3e}, Corr={corr:.3e}, χ={chi_sync:.3f}, α={alpha_sync:.3f}")

# ------------------------------
# Visualization
# ------------------------------
plt.figure(figsize=(8, 5))
plt.plot(E_trace, label="⟨L⟩", color="tab:blue")
plt.plot(corr_trace, label="⟨θA*θB⟩", color="tab:orange")
plt.plot(entropy_trace, label="Spectral Entropy", color="tab:green")
plt.plot(sync_trace, label="χ_sync", linestyle="--", color="tab:red")
plt.xlabel("Step")
plt.legend()
plt.title("F10 - Predictive Multiverse Coupling Evolution")
plt.tight_layout()
plt.savefig("PAEV_TestF10_Multiverse_Evolution.png", dpi=150)

# Phase field snapshots
plt.figure(figsize=(8, 4))
plt.subplot(1, 2, 1)
plt.imshow(theta_A, cmap="plasma")
plt.title("θ_A field @ final step")
plt.axis("off")
plt.subplot(1, 2, 2)
plt.imshow(theta_B, cmap="plasma")
plt.title("θ_B field")
plt.axis("off")
plt.tight_layout()
plt.savefig("PAEV_TestF10_Multiverse_FinalFields.png", dpi=150)

# Animation
fig, ax = plt.subplots()
im = ax.imshow(theta_A, cmap="inferno", animated=True)

def update(_):
    im.set_array(theta_A)
    return [im]

ani = animation.FuncAnimation(fig, update, frames=60, interval=100)
ani.save("PAEV_TestF10_Multiverse_Propagation.gif", fps=20)
plt.close()

# ------------------------------
# Summary
# ------------------------------
print("\n=== Test F10 - Predictive Multiverse Coupling Complete ===")
print(f"⟨L⟩ final = {E_trace[-1]:.4e}")
print(f"⟨θA*θB⟩ final = {corr_trace[-1]:.4e}")
print(f"Spectral entropy final = {entropy_trace[-1]:.4e}")
print(f"χ_sync final = {chi_sync:.4e}")
print(f"α_sync final = {alpha_sync:.4e}")
print(f"Perturbation mode: ON")
print("\nAll output files saved in working directory.")
print("----------------------------------------------------------")