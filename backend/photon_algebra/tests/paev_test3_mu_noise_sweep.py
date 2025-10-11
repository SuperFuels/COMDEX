#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 3μ — Measurement Stability Sweep (μ-noise → visibility)
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.visibility import project_with_pi

# ---------------------------------------------------------------
# μ — measurement noise interpreted as phase instability (σ)
# ---------------------------------------------------------------

def generate_with_noise(sigma, n_samples=256):
    """
    Simulate double-slit interference under phase noise σ.
    Phase noise varies along x to model decoherence.
    """
    x = np.linspace(-np.pi, np.pi, n_samples)
    slit1 = np.sin(5 * x)
    phase_noise = np.random.normal(0, sigma, size=x.shape)
    slit2 = np.sin(5 * x + phase_noise)

    # Sum coherent fields, compute intensity
    intensity = (slit1 + slit2) ** 2

    # Normalize each frame independently
    return intensity / np.max(intensity)


def run():
    sigmas = [0.0, 0.2, 0.5, 1.0]
    V = []

    os.makedirs("docs/theory/figures", exist_ok=True)
    os.makedirs("docs/theory/tables", exist_ok=True)

    for s in sigmas:
        # Create noisy frame stack
        stack = np.array([generate_with_noise(s) for _ in range(100)])
        proj = project_with_pi(stack)        # symbolic π projection

        # Mean intensity after projection
        intensity = proj.mean(axis=0)

        # Proper visibility formula
        Imax, Imin = np.max(intensity), np.min(intensity)
        V_value = (Imax - Imin) / (Imax + Imin + 1e-12)  # small epsilon avoids divide-by-zero

        V.append(V_value)
        print(f"σ={s:.2f} → Visibility V={V_value:.3f}")

    # Plot results
    plt.figure(figsize=(6, 4))
    plt.plot(sigmas, V, marker="o", linewidth=2)
    plt.xlabel("Phase noise σ (radians)")
    plt.ylabel("Visibility V")
    plt.title("μ-Stability Sweep — Phase Noise vs Visibility")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("docs/theory/figures/PAEV_Test3_MuNoise.png", dpi=300)
    print("✅ Saved figure to docs/theory/figures/PAEV_Test3_MuNoise.png")

    # Save CSV table
    np.savetxt(
        "docs/theory/tables/PAEV_Test3_MuNoise.csv",
        np.column_stack([sigmas, V]),
        delimiter=",",
        header="sigma,visibility",
        fmt="%.4f",
        comments=""
    )
    print("✅ Saved table to docs/theory/tables/PAEV_Test3_MuNoise.csv")


if __name__ == "__main__":
    run()