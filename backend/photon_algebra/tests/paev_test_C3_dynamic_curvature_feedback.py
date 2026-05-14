#!/usr/bin/env python3
"""
Test C3 - Dynamic Curvature Feedback (Symbolic Einstein Analogue)
------------------------------------------------------------------
Goal:
  Show how curvature κ(x) and rewrite distance D_rw(x) can co-evolve
  toward a self-consistent equilibrium - an algebraic analogue of
  Einstein's equation G ≈ T.

Mechanism:
  - Rewrite distance D_rw is computed by diffusive propagation.
  - Curvature field κ(x) evolves according to:
        dκ/dt = η * (D_rw - <D_rw>)
    which drives κ up where rewrites "feel long," and down where
    rewrites are short (local cost is low).

Outputs:
  1. Heatmaps of curvature κ(x) evolution at selected iterations.
  2. Correlation r(t) between κ(x) and rewrite potential D_rw(x).
  3. Stability curve: mean-square Δκ vs time.

Artifacts:
  - PAEV_TestC3_CurvatureFeedback_Evolution.png
  - PAEV_TestC3_CurvatureFeedback_Correlation.png
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate

# ----------------------------------------------------------
# Utilities
# ----------------------------------------------------------
def laplacian(arr):
    """Discrete 2-D Laplacian with Neumann boundary conditions."""
    lap = (
        -4 * arr
        + np.roll(arr, 1, axis=0)
        + np.roll(arr, -1, axis=0)
        + np.roll(arr, 1, axis=1)
        + np.roll(arr, -1, axis=1)
    )
    lap[0, :] = lap[1, :]
    lap[-1, :] = lap[-2, :]
    lap[:, 0] = lap[:, 1]
    lap[:, -1] = lap[:, -2]
    return lap

def normalize_field(f):
    fmin, fmax = np.min(f), np.max(f)
    return (f - fmin) / (fmax - fmin + 1e-12)

def pearson_r(a, b):
    a = a - np.mean(a)
    b = b - np.mean(b)
    return np.sum(a * b) / np.sqrt(np.sum(a * a) * np.sum(b * b) + 1e-15)

# ----------------------------------------------------------
# Rewrite propagation (diffusion-like)
# ----------------------------------------------------------
def rewrite_distance(kappa, n_iter=150):
    """
    Simulate rewrite propagation under local curvature cost (1+kappa).
    D_rw evolves via a diffusion-like process with variable speed.
    """
    N = kappa.shape[0]
    D = np.zeros_like(kappa)
    w = 1.0 + kappa
    for _ in range(n_iter):
        D += 0.05 * laplacian(D / (w + 1e-9) + 1.0)
    return D

# ----------------------------------------------------------
# Dynamic curvature feedback
# ----------------------------------------------------------
def evolve_curvature(N=81, amp=1.5, sigma=10.0, n_steps=50, eta=0.02):
    """
    Iteratively update curvature κ(x) according to rewrite distance feedback.
    """
    # initial curvature bump
    y, x = np.mgrid[0:N, 0:N]
    cx, cy = N//2, N//2
    r2 = (x - cx)**2 + (y - cy)**2
    kappa = amp * np.exp(-r2 / (2 * sigma**2))

    corr_hist = []
    mse_hist = []
    snapshots = []

    for t in range(n_steps):
        D_rw = rewrite_distance(kappa, n_iter=60)
        D_rw_n = normalize_field(D_rw)
        kappa_n = normalize_field(kappa)

        corr = pearson_r(D_rw_n, kappa_n)
        corr_hist.append(corr)

        # feedback update: curvature follows rewrite distance deviations
        dK = eta * (D_rw_n - np.mean(D_rw_n))
        kappa += dK

        mse_hist.append(np.mean(dK**2))
        if t in (0, n_steps//4, n_steps//2, n_steps-1):
            snapshots.append(normalize_field(kappa.copy()))

    return snapshots, corr_hist, mse_hist, kappa, D_rw_n

# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
if __name__ == "__main__":
    print("=== Test C3 - Dynamic Curvature Feedback (Symbolic Einstein Analogue) ===")
    N = 81
    amp = 1.5
    sigma = 10.0
    eta = 0.02
    n_steps = 40

    snaps, corrs, mses, kappa_final, D_final = evolve_curvature(
        N=N, amp=amp, sigma=sigma, n_steps=n_steps, eta=eta
    )

    print(f"Lattice {N}*{N}, η={eta}, steps={n_steps}")
    print(f"Final Pearson r(κ, D_rw) = {corrs[-1]:.4f}")
    print(f"Mean square Δκ at last step = {mses[-1]:.4e}")

    # --- Plot curvature evolution ---
    fig, axs = plt.subplots(1, len(snaps), figsize=(13, 4))
    for i, snap in enumerate(snaps):
        im = axs[i].imshow(snap, cmap="inferno")
        axs[i].set_title(f"κ(x) at t={int(i*(n_steps/len(snaps)))}")
        axs[i].axis("off")
        fig.colorbar(im, ax=axs[i], fraction=0.046, pad=0.04)
    plt.suptitle("Test C3 - Curvature Evolution under Rewrite Feedback")
    plt.tight_layout()
    plt.savefig("PAEV_TestC3_CurvatureFeedback_Evolution.png", dpi=160)
    print("✅ Saved plot to: PAEV_TestC3_CurvatureFeedback_Evolution.png")

    # --- Plot correlation + stability curves ---
    fig, ax1 = plt.subplots(figsize=(7, 4.2))
    t = np.arange(len(corrs))
    ax1.plot(t, corrs, "b-", lw=2, label="r(κ, D_rw)")
    ax1.set_xlabel("Iteration")
    ax1.set_ylabel("Correlation (r)", color="b")
    ax1.tick_params(axis="y", labelcolor="b")

    ax2 = ax1.twinx()
    ax2.plot(t, mses, "r--", lw=2, label="MSE(Δκ)")
    ax2.set_ylabel("Mean square Δκ", color="r")
    ax2.tick_params(axis="y", labelcolor="r")

    plt.title("Test C3 - Curvature-Rewrite Coupling Convergence")
    plt.tight_layout()
    plt.savefig("PAEV_TestC3_CurvatureFeedback_Correlation.png", dpi=160)
    print("✅ Saved plot to: PAEV_TestC3_CurvatureFeedback_Correlation.png")