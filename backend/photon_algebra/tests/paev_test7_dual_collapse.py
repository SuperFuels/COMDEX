#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 7 — Photon–Wave Dual Collapse (∇ μ → π)
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.visibility import compute_visibility, project_with_pi

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------
os.makedirs("docs/theory/figures", exist_ok=True)
os.makedirs("docs/theory/tables", exist_ok=True)

print("⚙️ Running PAEV Test 7 — Photon–Wave Dual Collapse (∇ μ → π)...")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------
W = 512
x = np.linspace(-np.pi, np.pi, W)
freq = 14
mu_levels = [0.0, 0.05, 0.1, 0.2]

# ---------------------------------------------------------------------
# Field generation across coupling regimes
# ---------------------------------------------------------------------
def generate_field(mode="decoupled", mu=0.1):
    phi = 2 * np.pi * freq * x
    noise = np.random.normal(0, mu, size=x.shape)

    if mode == "decoupled":
        A = 0.5 + 0.5 * np.cos(phi + np.random.rand() * 2 * np.pi)
    elif mode == "resonant":
        A = 0.5 + 0.5 * np.cos(phi + 0.5 * noise)
    elif mode == "entangled":
        shared = np.random.normal(0, mu / 2, size=x.shape)
        A = 0.5 + 0.5 * np.cos(phi + shared)
    else:
        raise ValueError("Unknown mode")
    return np.clip(A, 0, 1)

# ---------------------------------------------------------------------
# Collapse simulation — π projection after μ perturbation
# ---------------------------------------------------------------------
def collapse_and_measure(mode, mu):
    I_wave = generate_field(mode, mu)
    # inject decoherence proportional to μ
    noise2D = np.random.normal(0, mu, (I_wave.size, I_wave.size))
    I2D = np.tile(I_wave, (I_wave.size, 1))
    I2D *= (1 + 0.2 * noise2D)      # simulate μ–dependent fluctuation
    I_proj2D = project_with_pi(I2D, pi_spatial=4)
    I_proj = np.mean(I_proj2D, axis=0)
    V_wave = compute_visibility(I_wave)
    V_proj = compute_visibility(I_proj)
    return V_wave, V_proj

# ---------------------------------------------------------------------
# Run suite
# ---------------------------------------------------------------------
modes = ["decoupled", "resonant", "entangled"]
results = {m: {"μ": [], "V_wave": [], "V_proj": []} for m in modes}

for mode in modes:
    for mu in mu_levels:
        Vw, Vp = collapse_and_measure(mode, mu)
        results[mode]["μ"].append(mu)
        results[mode]["V_wave"].append(Vw)
        results[mode]["V_proj"].append(Vp)
        print(f"{mode:<10s} μ={mu:<.2f} → V_wave={Vw:.3f}, V_proj={Vp:.3f}")

# ---------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4))

for mode, color in zip(modes, ["#607d8b", "#4caf50", "#9c27b0"]):
    axes[0].plot(results[mode]["μ"], results[mode]["V_wave"], "-o", label=mode, color=color)
    axes[1].plot(results[mode]["μ"], results[mode]["V_proj"], "-o", label=mode, color=color)

axes[0].set_title("Wave-domain Visibility ⟨V_wave⟩")
axes[1].set_title("After Collapse (π Projection) ⟨V_proj⟩")

for ax in axes:
    ax.set_xlabel("Phase noise μ")
    ax.set_ylabel("Visibility V")
    ax.grid(alpha=0.3)
    ax.legend()

plt.suptitle("Test 7 — Photon–Wave Dual Collapse (∇ μ → π)")
plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test7_DualCollapse.png", dpi=300)
print("✅ Saved figure to docs/theory/figures/PAEV_Test7_DualCollapse.png")

# ---------------------------------------------------------------------
# Save table
# ---------------------------------------------------------------------
table_path = "docs/theory/tables/PAEV_Test7_DualCollapse.csv"
with open(table_path, "w") as f:
    f.write("mode,mu,V_wave,V_proj\n")
    for mode in modes:
        for mu, Vw, Vp in zip(results[mode]["μ"], results[mode]["V_wave"], results[mode]["V_proj"]):
            f.write(f"{mode},{mu:.3f},{Vw:.6f},{Vp:.6f}\n")
print(f"✅ Saved table to {table_path}")
print("🏁 PAEV Test 7 complete.")