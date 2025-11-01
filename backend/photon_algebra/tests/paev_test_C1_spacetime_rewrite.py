#!/usr/bin/env python3
"""
Test C1 - Spacetime Rewrite Equivalence (Toy Discrete Manifold)

Goal
----
Show that a contextual, deterministic rewrite process (Photon Algebra style)
induces an effective distance that tracks a geometric metric on a curved
discrete manifold.

Setup
-----
- 2D lattice (NxN) with coordinates (i,j), i,j ∈ {0..N-1}.
- Synthetic curvature field κ(i,j): a Gaussian "mass" bump.
- Geometric cost (local line element): w(i,j) = 1 + κ(i,j) >= 1.
- Geodesic distance from a source s via Dijkstra using edge cost = average of w.

Rewrite metric
--------------
- Start a unit "token mass" at source cell s.
- Per step:
    * From each active cell, distribute its mass to 4-neighbors with weights
      proportional to 1 / w(neighbor) (context favors "low curvature/low cost").
    * A cell's *arrival time* is the first step when its cumulative mass exceeds
      a small threshold ε (idempotent-trigger / normalization event).
- Rewrite distance D_RW(cell) = first-arrival step index.
- Compare D_RW vs geometric distance D_GEO.

Outputs
-------
- Prints Pearson r, MSE between normalized distances.
- Saves:
    * PAEV_TestC1_SpacetimeRewrite_Heatmaps.png
    * PAEV_TestC1_SpacetimeRewrite_Scatter.png
"""

import numpy as np
import matplotlib.pyplot as plt
from heapq import heappush, heappop

# ------------------------------
# Lattice & curvature
# ------------------------------
def gaussian_bump(N, cx, cy, sigma, amp):
    Y, X = np.mgrid[0:N, 0:N]
    r2 = (X - cx)**2 + (Y - cy)**2
    return amp * np.exp(-r2 / (2*sigma*sigma))

def neighbors(i, j, N):
    if i > 0:     yield (i-1, j)
    if i < N-1:   yield (i+1, j)
    if j > 0:     yield (i, j-1)
    if j < N-1:   yield (i, j+1)

# ------------------------------
# Geometric distance via Dijkstra
# ------------------------------
def dijkstra_geodesic(w, src):
    """
    w[i,j] >= 1 is local weight (line element multiplier).
    Edge cost between p and q uses average weight.
    Returns distance array D_GEO of shape (N,N).
    """
    N = w.shape[0]
    INF = 1e30
    dist = np.full((N,N), INF, dtype=float)
    sx, sy = src
    dist[sx, sy] = 0.0
    pq = []
    heappush(pq, (0.0, (sx, sy)))
    while pq:
        d, (i, j) = heappop(pq)
        if d > dist[i,j]:
            continue
        for (u, v) in neighbors(i, j, N):
            # edge cost = average of weights (unit grid spacing)
            c = 0.5 * (w[i,j] + w[u,v])
            nd = d + c
            if nd < dist[u,v]:
                dist[u,v] = nd
                heappush(pq, (nd, (u, v)))
    return dist

# ------------------------------
# Rewrite distance (deterministic, contextual)
# ------------------------------
def rewrite_distance(w, src, eps=1e-4, max_steps=2000):
    """
    Deterministic "flow" of a unit token from source:
    - At step t, each cell distributes its mass to neighbors with weights
      proportional to 1 / w(neighbor) (favoring low-cost geometry).
    - First-arrival time when cumulative mass at a cell exceeds eps.

    Returns: arrival_step (N,N) with np.inf for cells never reached.
    """
    N = w.shape[0]
    sx, sy = src
    invw = 1.0 / w

    cur = np.zeros((N,N), dtype=float)
    cur[sx, sy] = 1.0
    cum = np.zeros((N,N), dtype=float)
    arrival = np.full((N,N), np.inf, dtype=float)

    for step in range(1, max_steps+1):
        nxt = np.zeros_like(cur)
        # distribute
        it = np.ndindex(N,N)
        for i, j in it:
            m = cur[i,j]
            if m <= 0.0:
                continue
            # neighbor weights ∝ invw
            neigh = list(neighbors(i, j, N))
            if not neigh:
                continue
            weights = np.array([invw[u,v] for (u,v) in neigh], dtype=float)
            S = weights.sum()
            if S <= 0:
                continue
            frac = weights / S
            for k, (u, v) in enumerate(neigh):
                nxt[u,v] += m * float(frac[k])

        # update cumulative and arrival times
        cum += nxt
        newly = (arrival == np.inf) & (cum >= eps)
        arrival[newly] = step

        cur = nxt
        if np.all(arrival < np.inf):
            break

    return arrival

# ------------------------------
# Metrics & plots
# ------------------------------
def correlate(a, b):
    a1 = (a - a.mean()) / (a.std() + 1e-12)
    b1 = (b - b.mean()) / (b.std() + 1e-12)
    return float(np.mean(a1 * b1))

def main():
    # --- lattice & curvature ---
    N = 61
    cx, cy = (N//2 + 6, N//2)        # off-center bump
    sigma = 9.0
    amp = 1.5                        # curvature amplitude
    kappa = gaussian_bump(N, cx, cy, sigma, amp)  # "mass/curvature"
    w = 1.0 + kappa                  # local cost >= 1

    src = (N//2, N//2 - 18)          # source to the left of the bump

    # --- distances ---
    D_geo = dijkstra_geodesic(w, src)
    D_rw_steps = rewrite_distance(w, src, eps=1e-4, max_steps=4000)

    # mask unreachable (shouldn't happen), normalize both to [0,1] for comparison
    geo = D_geo.copy()
    rw = D_rw_steps.copy()
    # avoid infinities
    msk = np.isfinite(rw) & np.isfinite(geo)
    geo = geo[msk]
    rw = rw[msk]

    # ✅ NumPy 2.0 fix: use np.ptp() instead of ndarray.ptp()
    geo_n = (geo - geo.min()) / (np.ptp(geo) + 1e-12)
    rw_n  = (rw  - rw.min())  / (np.ptp(rw)  + 1e-12)

    r = correlate(geo_n, rw_n)
    mse = float(np.mean((geo_n - rw_n)**2))

    print("=== Test C1 - Spacetime Rewrite Equivalence (Toy Manifold) ===")
    print(f"Lattice: {N}x{N}, Gaussian curvature bump amp={amp}, sigma={sigma}")
    print(f"Source at {src}")
    print(f"Pearson r( D_geo , D_rw )   = {r:.4f}")
    print(f"MSE( normalized distances ) = {mse:.4e}")

    # --- Heatmaps side-by-side ---
    fig, axs = plt.subplots(1, 3, figsize=(12, 4.1))

    im0 = axs[0].imshow(1.0 + kappa, cmap="viridis")
    axs[0].set_title("Local cost w = 1+κ")
    axs[0].axis('off')
    fig.colorbar(im0, ax=axs[0], fraction=0.046, pad=0.04)

    im1 = axs[1].imshow(D_geo, cmap="magma")
    axs[1].plot(src[1], src[0], 'wo', ms=4)
    axs[1].set_title("Geodesic distance D_GEO")
    axs[1].axis('off')
    fig.colorbar(im1, ax=axs[1], fraction=0.046, pad=0.04)

    im2 = axs[2].imshow(D_rw_steps, cmap="magma")
    axs[2].plot(src[1], src[0], 'wo', ms=4)
    axs[2].set_title("Rewrite distance (arrival steps)")
    axs[2].axis('off')
    fig.colorbar(im2, ax=axs[2], fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.savefig("PAEV_TestC1_SpacetimeRewrite_Heatmaps.png", dpi=180)
    print("✅ Saved plot to: PAEV_TestC1_SpacetimeRewrite_Heatmaps.png")

    # --- Scatter plot ---
    plt.figure(figsize=(6.4, 4.6))
    plt.scatter(geo_n, rw_n, s=6, alpha=0.35, label="cells")

    # best-fit line
    A = np.vstack([geo_n, np.ones_like(geo_n)]).T
    a, b = np.linalg.lstsq(A, rw_n, rcond=None)[0]
    xs = np.linspace(0, 1, 200)
    plt.plot(xs, a*xs + b, 'r-', lw=2, label=f"fit: y≈{a:.2f}x+{b:.2f}")

    plt.xlabel("Geodesic distance (normalized)")
    plt.ylabel("Rewrite distance (normalized)")
    plt.title("Test C1 - Rewrite vs Geodesic Distance")
    plt.legend()
    plt.tight_layout()
    plt.savefig("PAEV_TestC1_SpacetimeRewrite_Scatter.png", dpi=180)
    print("✅ Saved plot to: PAEV_TestC1_SpacetimeRewrite_Scatter.png")

if __name__ == "__main__":
    main()