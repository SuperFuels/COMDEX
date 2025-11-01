#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 4 - Resonant Coupling (⟲) and Entanglement (↔) Stability
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.visibility import compute_visibility

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------
os.makedirs("docs/theory/figures", exist_ok=True)
os.makedirs("docs/theory/tables", exist_ok=True)

print("⚙️ Running PAEV Test 4 - Resonant Coupling and Entanglement Stability...")

# ---------------------------------------------------------------------
# Simulation Parameters
# ---------------------------------------------------------------------
N = 512
NTRIALS = 16
rng = np.random.default_rng(42)

x = np.linspace(-np.pi, np.pi, N)
freq_A, freq_B = 12, 12.3   # slightly offset frequencies
noise_level = 0.05

# ---------------------------------------------------------------------
# Generate field pairs
# ---------------------------------------------------------------------
def generate_field_pair(mode="decoupled"):
    """Generate two 1D interference fields in different coupling regimes."""
    phi_A = 2 * np.pi * freq_A * x
    phi_B = 2 * np.pi * freq_B * x

    if mode == "decoupled":
        A = 0.5 + 0.5 * np.cos(phi_A + rng.normal(0, noise_level))
        B = 0.5 + 0.5 * np.cos(phi_B + rng.normal(0, noise_level))

    elif mode == "resonant":
        # partial phase-lock (resonant coherence)
        coupling = 0.6
        phase_shift = rng.uniform(-np.pi, np.pi)
        A = 0.5 + 0.5 * np.cos(phi_A)
        B = 0.5 + 0.5 * np.cos(phi_B * (1 - coupling) + phi_A * coupling + phase_shift)

    elif mode == "entangled":
        # share both π-projection and μ-noise (common phase term)
        shared_phase = rng.normal(0, noise_level, size=x.shape)
        A = 0.5 + 0.5 * np.cos(phi_A + shared_phase)
        B = 0.5 + 0.5 * np.cos(phi_A + shared_phase + np.pi / 8)

    else:
        raise ValueError(f"Unknown mode: {mode}")

    return np.clip(A, 0, 1), np.clip(B, 0, 1)


# ---------------------------------------------------------------------
# Correlation visibility
# ---------------------------------------------------------------------
def correlation_visibility(A, B):
    """Compute normalized correlation visibility between two fields."""
    cov = np.cov(A, B)[0, 1]
    return cov / (np.std(A) * np.std(B) + 1e-12)


# ---------------------------------------------------------------------
# Multi-trial averaging
# ---------------------------------------------------------------------
modes = ["decoupled", "resonant", "entangled"]
V_A_mean, V_B_mean, V_corr_mean, V_corr_std = [], [], [], []

for mode in modes:
    vis_A, vis_B, vis_corr = [], [], []
    for _ in range(NTRIALS):
        A, B = generate_field_pair(mode)
        vis_A.append(compute_visibility(A))
        vis_B.append(compute_visibility(B))
        vis_corr.append(correlation_visibility(A, B))

    V_A_mean.append(np.mean(vis_A))
    V_B_mean.append(np.mean(vis_B))
    V_corr_mean.append(np.mean(vis_corr))
    V_corr_std.append(np.std(vis_corr))

    print(f"{mode:<10s} -> "
          f"⟨V_A⟩={np.mean(vis_A):.3f}, "
          f"⟨V_B⟩={np.mean(vis_B):.3f}, "
          f"⟨V_corr⟩={np.mean(vis_corr):.3f} ± {np.std(vis_corr):.3f}")


# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------
plt.figure(figsize=(6, 4))
plt.bar(modes, V_corr_mean, yerr=V_corr_std,
        color=["#607d8b", "#4caf50", "#9c27b0"], capsize=6)
plt.ylabel("Correlation Visibility $V_c$")
plt.title("Test 4 - Resonant Coupling (⟲) and Entanglement (↔) Stability")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test4_ResonantCoupling.png", dpi=300)
print("✅ Saved figure to docs/theory/figures/PAEV_Test4_ResonantCoupling.png")


# ---------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------
table_path = "docs/theory/tables/PAEV_Test4_ResonantCoupling.csv"
np.savetxt(
    table_path,
    np.column_stack([np.arange(len(modes)), V_A_mean, V_B_mean, V_corr_mean, V_corr_std]),
    delimiter=",",
    header="index,V_A_mean,V_B_mean,V_corr_mean,V_corr_std",
    fmt="%.4f",
    comments=""
)
print(f"✅ Saved table to {table_path}")
print("🏁 PAEV Test 4 complete.")