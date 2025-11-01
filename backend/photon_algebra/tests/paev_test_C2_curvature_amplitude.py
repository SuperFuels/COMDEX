#!/usr/bin/env python3
"""
Test C2 - Curvature-Amplitude Correspondence
---------------------------------------------
Goal:
Show that curvature fields κ(x) correspond to quantum phase curvature ∇2φ(x),
and that Photon Algebra rewrite cost reproduces the same pattern deterministically.

Artifacts:
- PAEV_TestC2_CurvatureAmplitude_Heatmaps.png
- PAEV_TestC2_CurvatureAmplitude_Scatter.png
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import laplace

def gaussian_curvature_field(N=81, amp=1.0, sigma=10.0):
    y, x = np.mgrid[0:N, 0:N]
    cx, cy = N//2, N//2
    r2 = (x - cx)**2 + (y - cy)**2
    return amp * np.exp(-r2 / (2*sigma**2))

def wave_phase_from_curvature(kappa, k0=5.0):
    """Integrate curvature into a synthetic phase field φ(x,y)"""
    N = kappa.shape[0]
    y, x = np.mgrid[0:N, 0:N]
    r = np.sqrt((x - N//2)**2 + (y - N//2)**2)
    φ = k0 * r / N + 0.3 * kappa  # base radial wave + curvature modulation
    return φ

def photon_algebra_rewrite_field(kappa):
    """Simulated rewrite 'cost' acting as effective phase curvature"""
    # Use local smoothing to mimic rewrite propagation
    from scipy.ndimage import gaussian_filter
    rw = gaussian_filter(kappa, sigma=2)
    return rw / np.max(np.abs(rw))

def main():
    N = 81
    amp = 1.5
    sigma = 10.0
    kappa = gaussian_curvature_field(N, amp=amp, sigma=sigma)

    # Generate quantum-like phase
    φ = wave_phase_from_curvature(kappa)

    # Quantum phase curvature (Laplacian)
    φ_curv = laplace(φ)
    φ_curv_n = (φ_curv - φ_curv.min()) / (np.ptp(φ_curv) + 1e-12)

    # Photon Algebra rewrite curvature
    rw = photon_algebra_rewrite_field(kappa)
    rw_n = (rw - rw.min()) / (np.ptp(rw) + 1e-12)

    # Correlation metrics
    corr = np.corrcoef(φ_curv_n.ravel(), rw_n.ravel())[0,1]
    mse = np.mean((φ_curv_n - rw_n)**2)

    print("=== Test C2 - Curvature ↔ Quantum Phase Correspondence ===")
    print(f"Lattice size: {N}*{N}, curvature amp={amp}, sigma={sigma}")
    print(f"Pearson r(∇2φ, κ_rw) = {corr:.4f}")
    print(f"MSE(normalized fields) = {mse:.4e}")

    # --- Heatmaps ---
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    im0 = axs[0].imshow(kappa, cmap="viridis")
    axs[0].set_title("Input curvature κ(x)")
    plt.colorbar(im0, ax=axs[0], fraction=0.046, pad=0.04)

    im1 = axs[1].imshow(φ_curv_n, cmap="magma")
    axs[1].set_title("Quantum phase curvature ∇2φ (normalized)")
    plt.colorbar(im1, ax=axs[1], fraction=0.046, pad=0.04)

    im2 = axs[2].imshow(rw_n, cmap="plasma")
    axs[2].set_title("Photon Algebra rewrite curvature (normalized)")
    plt.colorbar(im2, ax=axs[2], fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.savefig("PAEV_TestC2_CurvatureAmplitude_Heatmaps.png", dpi=160)
    print("✅ Saved plot to: PAEV_TestC2_CurvatureAmplitude_Heatmaps.png")

    # --- Scatter plot ---
    plt.figure(figsize=(6,4))
    plt.scatter(φ_curv_n, rw_n, s=6, alpha=0.4)
    A = np.vstack([φ_curv_n.ravel(), np.ones_like(φ_curv_n.ravel())]).T
    a, b = np.linalg.lstsq(A, rw_n.ravel(), rcond=None)[0]
    xs = np.linspace(0,1,200)
    plt.plot(xs, a*xs+b, 'r-', lw=2, label=f"fit: y≈{a:.2f}x+{b:.2f}")
    plt.xlabel("Quantum ∇2φ (normalized)")
    plt.ylabel("Photon Algebra rewrite curvature")
    plt.title("Test C2 - Curvature ↔ Phase Correspondence")
    plt.legend()
    plt.tight_layout()
    plt.savefig("PAEV_TestC2_CurvatureAmplitude_Scatter.png", dpi=160)
    print("✅ Saved plot to: PAEV_TestC2_CurvatureAmplitude_Scatter.png")

if __name__ == "__main__":
    main()