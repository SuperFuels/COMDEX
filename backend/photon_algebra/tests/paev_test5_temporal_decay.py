#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 5 - Temporal Coherence Decay (μ-⟲-↔ Coupled Dynamics)
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
print("⚙️ Running PAEV Test 5 - Temporal Coherence Decay (μ-⟲-↔ dynamics)...")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------
T = 200                     # time steps
N = 512                     # spatial samples per frame
freq = 10                   # base spatial frequency
noise_levels = [0.01, 0.05, 0.1]   # μ-noise strengths
kappa_res = 0.4             # ⟲ resonance coupling
rng = np.random.default_rng(42)
x = np.linspace(-np.pi, np.pi, N)
t = np.linspace(0, 10, T)

# ---------------------------------------------------------------------
# Core temporal evolution
# ---------------------------------------------------------------------
def evolve_fields(mu=0.05, coupling="decoupled"):
    """Generate temporal field pairs A(t), B(t) with given μ-noise and coupling."""
    A_frames, B_frames = [], []
    phi_base = 2 * np.pi * freq * x

    shared_phase = np.zeros_like(x)
    for i, ti in enumerate(t):
        # time-dependent μ-noise
        noise = rng.normal(0, mu, size=x.shape)
        shared_phase += noise

        if coupling == "decoupled":
            A = 0.5 + 0.5 * np.cos(phi_base + rng.normal(0, mu))
            B = 0.5 + 0.5 * np.cos(phi_base + rng.normal(0, mu))

        elif coupling == "resonant":
            # partial phase exchange through ⟲
            phase_B = phi_base * (1 - kappa_res) + phi_base * kappa_res + shared_phase
            A = 0.5 + 0.5 * np.cos(phi_base + shared_phase)
            B = 0.5 + 0.5 * np.cos(phase_B)

        elif coupling == "entangled":
            # perfect shared μ-phase -> correlated evolution
            A = 0.5 + 0.5 * np.cos(phi_base + shared_phase)
            B = 0.5 + 0.5 * np.cos(phi_base + shared_phase + np.pi / 12)
        else:
            raise ValueError(f"Unknown coupling mode {coupling}")

        A_frames.append(A)
        B_frames.append(B)

    return np.array(A_frames), np.array(B_frames)

# ---------------------------------------------------------------------
# Measure coherence vs time
# ---------------------------------------------------------------------
def correlation_visibility(A, B):
    """Instantaneous normalized correlation."""
    return np.cov(A, B)[0, 1] / (np.std(A) * np.std(B) + 1e-12)

def measure_temporal_decay(mu, mode):
    A_stack, B_stack = evolve_fields(mu=mu, coupling=mode)
    V_local, V_corr = [], []
    for Ai, Bi in zip(A_stack, B_stack):
        V_local.append((compute_visibility(Ai) + compute_visibility(Bi)) / 2)
        V_corr.append(correlation_visibility(Ai, Bi))
    return np.array(V_local), np.array(V_corr)

# ---------------------------------------------------------------------
# Run for all couplings
# ---------------------------------------------------------------------
modes = ["decoupled", "resonant", "entangled"]
results = {}

for mode in modes:
    Vt_all, Vc_all = [], []
    for mu in noise_levels:
        Vt, Vc = measure_temporal_decay(mu, mode)
        Vt_all.append(Vt)
        Vc_all.append(Vc)
    results[mode] = {"Vt": np.array(Vt_all), "Vc": np.array(Vc_all)}

# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4))

for i, mode in enumerate(modes):
    Vc_mean = results[mode]["Vc"].mean(axis=0)
    axes[0].plot(t, Vc_mean, label=f"{mode}")
axes[0].set_title("Temporal Cross-Correlation Decay")
axes[0].set_xlabel("Time t (arb)")
axes[0].set_ylabel("⟨V(c)(t)⟩")
axes[0].legend()
axes[0].grid(alpha=0.3)

for i, mu in enumerate(noise_levels):
    Vt_mean = np.mean([results[m]["Vt"][i] for m in modes], axis=0)
    axes[1].plot(t, Vt_mean, label=f"μ={mu}")
axes[1].set_title("Average Local Visibility Decay")
axes[1].set_xlabel("Time t (arb)")
axes[1].set_ylabel("⟨V(t)⟩")
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test5_TemporalDecay.png", dpi=300)
print("✅ Saved figure to docs/theory/figures/PAEV_Test5_TemporalDecay.png")

# ---------------------------------------------------------------------
# Export summary CSV
# ---------------------------------------------------------------------
table_path = "docs/theory/tables/PAEV_Test5_TemporalDecay.csv"
with open(table_path, "w") as f:
    f.write("time," + ",".join([f"Vc_{m}" for m in modes]) + "\n")
    for i, ti in enumerate(t):
        vals = [results[m]["Vc"].mean(axis=0)[i] for m in modes]
        f.write(f"{ti:.3f}," + ",".join(f"{v:.5f}" for v in vals) + "\n")

print(f"✅ Saved table to {table_path}")
print("🏁 PAEV Test 5 complete.")