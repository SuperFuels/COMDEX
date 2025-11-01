#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 6 - Fourier-Spectral Entanglement Bandwidth (μ-⟲-↔ domain)
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
print("⚙️ Running PAEV Test 6 - Spectral Entanglement Bandwidth analysis...")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------
T, N = 200, 512
freq = 10
mu = 0.05
kappa = 0.4
rng = np.random.default_rng(7)
x = np.linspace(-np.pi, np.pi, N)
t = np.linspace(0, 10, T)
dt = t[1] - t[0]
fs = 1 / dt

# ---------------------------------------------------------------------
# Temporal correlation traces (Vc vs t)
# ---------------------------------------------------------------------
def correlation_visibility(A, B):
    return np.cov(A, B)[0, 1] / (np.std(A) * np.std(B) + 1e-12)

def evolve_pair(mode):
    phi = 2 * np.pi * freq * x
    shared = np.zeros_like(x)
    Vc = []
    for _ in t:
        noise = rng.normal(0, mu, size=x.shape)
        shared += noise
        if mode == "decoupled":
            A = 0.5 + 0.5 * np.cos(phi + rng.normal(0, mu))
            B = 0.5 + 0.5 * np.cos(phi + rng.normal(0, mu))
        elif mode == "resonant":
            A = 0.5 + 0.5 * np.cos(phi + shared)
            B = 0.5 + 0.5 * np.cos(phi * (1 - kappa) + phi * kappa + shared)
        elif mode == "entangled":
            A = 0.5 + 0.5 * np.cos(phi + shared)
            B = 0.5 + 0.5 * np.cos(phi + shared + np.pi / 12)
        else:
            raise ValueError(f"Unknown mode {mode}")
        Vc.append(correlation_visibility(A, B))
    return np.array(Vc)

modes = ["decoupled", "resonant", "entangled"]
Vc_t = {m: evolve_pair(m) for m in modes}

# ---------------------------------------------------------------------
# Fourier analysis of Vc(t)
# ---------------------------------------------------------------------
freqs = np.fft.rfftfreq(T, d=dt)
Sc = {m: np.abs(np.fft.rfft(Vc_t[m] - Vc_t[m].mean())) for m in modes}
Sc_norm = {m: Sc[m] / np.max(Sc[m]) for m in modes}

# ---------------------------------------------------------------------
# Compute half-power bandwidth (Δf(1/2))
# ---------------------------------------------------------------------
def half_power_bw(S, f):
    th = 0.5
    mask = S >= th
    if np.any(mask):
        indices = np.where(mask)[0]
        bw = f[indices[-1]] - f[indices[0]]
    else:
        bw = 0.0
    return bw

bandwidths = {m: half_power_bw(Sc_norm[m], freqs) for m in modes}

# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(10, 4))

for m in modes:
    ax[0].plot(t, Vc_t[m], label=m)
ax[0].set_title("Temporal Correlation Traces $V_c(t)$")
ax[0].set_xlabel("Time t (arb)")
ax[0].set_ylabel("$V_c$")
ax[0].grid(alpha=0.3)
ax[0].legend()

for m in modes:
    ax[1].plot(freqs, Sc_norm[m], label=f"{m} Δf(1/2)={bandwidths[m]:.3f}")
ax[1].set_title("Spectral Coherence Density $S_c(f)$")
ax[1].set_xlabel("Frequency f (arb)")
ax[1].set_ylabel("Normalized Amplitude")
ax[1].legend()
ax[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test6_FourierSpectrum.png", dpi=300)
print("✅ Saved figure to docs/theory/figures/PAEV_Test6_FourierSpectrum.png")

# ---------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------
table_path = "docs/theory/tables/PAEV_Test6_FourierSpectrum.csv"
with open(table_path, "w") as f:
    f.write("mode,bw_half\n")
    for m in modes:
        f.write(f"{m},{bandwidths[m]:.6f}\n")

print(f"✅ Saved table to {table_path}")
print("🏁 PAEV Test 6 complete.")