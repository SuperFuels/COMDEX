#!/usr/bin/env python3
"""
Section C4 - Emergent Gravity from Local Rewrite Mass

Goal:
  Demonstrate that local "information density" (mass term M)
  induces curvature κ(x) that warps geodesic and rewrite distances.
  This acts as a symbolic analogue of gravitational wells.

Process:
  1. Define lattice with Gaussian mass term M(x).
  2. Evolve curvature κ(x,t) with a diffusion-mass feedback rule:
         κ_{t+1} = κ_t + η(α∇2κ_t + βM)
  3. Compute rewrite-distance field D_rw(x)
     from curvature-weighted propagation.
  4. Compare D_rw(x) to geodesic distance D_geo(x).
  5. Visualize how mass curvature affects spacetime rewrites.

Outputs:
  - Heatmaps for κ(x), M(x), and D_rw(x)
  - Correlation + MSE between curvature and rewrite metric
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import laplace
from scipy.stats import pearsonr
import heapq


# ---------- Utilities ----------
def normalize(a):
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    amin, amax = a.min(), a.max()
    if amax - amin < 1e-12:
        return np.zeros_like(a)
    return (a - amin) / (amax - amin)


def geodesic_distance(w, src):
    """Compute Dijkstra-like geodesic distance on lattice with cost w."""
    n, m = w.shape
    D = np.full((n, m), np.inf)
    visited = np.zeros_like(D, dtype=bool)
    pq = [(0.0, src)]
    D[src] = 0.0
    while pq:
        d, (i, j) = heapq.heappop(pq)
        if visited[i, j]:
            continue
        visited[i, j] = True
        for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
            ni, nj = i+di, j+dj
            if 0 <= ni < n and 0 <= nj < m and not visited[ni, nj]:
                nd = d + 0.5 * (w[i, j] + w[ni, nj])
                if nd < D[ni, nj]:
                    D[ni, nj] = nd
                    heapq.heappush(pq, (nd, (ni, nj)))
    return D


# ---------- Main ----------
def main():
    N = 81
    amp_mass = 5.0
    sigma_mass = 8.0
    alpha = 0.25
    beta = 0.75
    eta = 0.05
    steps = 60

    # Lattice coordinates
    x = np.linspace(-1, 1, N)
    X, Y = np.meshgrid(x, x)

    # Mass distribution (information density)
    M = amp_mass * np.exp(-(X**2 + Y**2) / (2 * (sigma_mass / N)**2))

    # Initialize curvature (flat space)
    kappa = np.zeros_like(M)

    # Source for geodesic/rewrite metrics
    src = (N//2, N//2)

    corr_hist = []
    for t in range(steps):
        # curvature diffusion + source term
        lap = laplace(kappa)
        kappa += eta * (alpha * lap + beta * M)
        kappa = np.clip(kappa, 0.0, None)

        # rewrite propagation cost
        w_rw = 1.0 + normalize(kappa)
        D_rw = geodesic_distance(w_rw, src)

        # correlation between curvature and rewrite metric
        mask = np.isfinite(D_rw)
        r = pearsonr(normalize(kappa[mask]), normalize(D_rw[mask]))[0]
        corr_hist.append(r)

    # Final metrics
    D_geo = geodesic_distance(1.0 + normalize(M), src)
    D_rw_final = geodesic_distance(1.0 + normalize(kappa), src)

    mask = np.isfinite(D_rw_final)
    geo_n = normalize(D_geo[mask])
    rw_n = normalize(D_rw_final[mask])
    r_final = pearsonr(geo_n, rw_n)[0]
    mse_final = np.mean((geo_n - rw_n)**2)

    print("=== Test C4 - Emergent Gravity from Rewrite Mass ===")
    print(f"Lattice {N}*{N}, steps={steps}, η={eta}, α={alpha}, β={beta}")
    print(f"Final Pearson r( D_geo , D_rw ) = {r_final:.4f}")
    print(f"MSE(normalized distances) = {mse_final:.4e}")

    # --- Visualizations ---
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    im0 = axs[0].imshow(normalize(M), cmap="viridis")
    axs[0].set_title("Mass distribution M(x)")
    axs[0].axis("off")
    fig.colorbar(im0, ax=axs[0], fraction=0.046, pad=0.04)

    im1 = axs[1].imshow(normalize(kappa), cmap="inferno")
    axs[1].set_title("Curvature κ(x) after evolution")
    axs[1].axis("off")
    fig.colorbar(im1, ax=axs[1], fraction=0.046, pad=0.04)

    im2 = axs[2].imshow(normalize(D_rw_final), cmap="magma")
    axs[2].plot(src[1], src[0], 'wo', ms=4)
    axs[2].set_title("Rewrite distance D_rw(x)")
    axs[2].axis("off")
    fig.colorbar(im2, ax=axs[2], fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.savefig("PAEV_TestC4_GravityWell_Heatmaps.png", dpi=180)
    print("✅ Saved plot to: PAEV_TestC4_GravityWell_Heatmaps.png")

    # Correlation history plot
    plt.figure(figsize=(6.4, 4.2))
    plt.plot(corr_hist, "b-", lw=2)
    plt.xlabel("Step")
    plt.ylabel("Correlation r(κ, D_rw)")
    plt.title("Test C4 - Gravity Well Correlation Convergence")
    plt.tight_layout()
    plt.savefig("PAEV_TestC4_GravityWell_Correlation.png", dpi=180)
    print("✅ Saved plot to: PAEV_TestC4_GravityWell_Correlation.png")


if __name__ == "__main__":
    main()