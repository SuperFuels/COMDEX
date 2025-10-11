#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 6B — Spectral Correlation Matrix (π–↔ cross-mapping)
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
print("⚙️ Running PAEV Test 6B — Spectral Correlation Matrix (π–↔ cross-mapping)...")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------
Nx, Nt = 256, 128
freq_spatial = 10
freq_temporal = 1.5
mu = 0.05
kappa = 0.4
rng = np.random.default_rng(9)

x = np.linspace(-np.pi, np.pi, Nx)
t = np.linspace(0, 8, Nt)
kx = np.fft.fftfreq(Nx, d=(x[1]-x[0]))
f = np.fft.fftfreq(Nt, d=(t[1]-t[0]))

# ---------------------------------------------------------------------
# Generate spatiotemporal fields
# ---------------------------------------------------------------------
def generate_pair(mode):
    phi_x = 2*np.pi*freq_spatial*x
    A, B = np.zeros((Nt, Nx)), np.zeros((Nt, Nx))
    shared_phase = np.zeros_like(x)

    for i, tt in enumerate(t):
        noise = rng.normal(0, mu, size=x.shape)
        shared_phase += noise
        if mode == "decoupled":
            A[i] = 0.5 + 0.5*np.cos(phi_x + rng.normal(0, mu))
            B[i] = 0.5 + 0.5*np.cos(phi_x + rng.normal(0, mu))
        elif mode == "resonant":
            A[i] = 0.5 + 0.5*np.cos(phi_x + shared_phase)
            B[i] = 0.5 + 0.5*np.cos(phi_x*(1-kappa) + phi_x*kappa + shared_phase)
        elif mode == "entangled":
            A[i] = 0.5 + 0.5*np.cos(phi_x + shared_phase)
            B[i] = 0.5 + 0.5*np.cos(phi_x + shared_phase + np.pi/6)
        else:
            raise ValueError(mode)
    return A, B

# ---------------------------------------------------------------------
# Compute cross-spectral density S_AB(k,f)
# ---------------------------------------------------------------------
def cross_spectral_density(A, B):
    F_A = np.fft.fft2(A - A.mean())
    F_B = np.fft.fft2(B - B.mean())
    S_AB = np.abs(np.fft.fftshift(F_A * np.conj(F_B)))
    return S_AB / np.max(S_AB)

modes = ["decoupled", "resonant", "entangled"]
maps = {}

for mode in modes:
    A, B = generate_pair(mode)
    S_AB = cross_spectral_density(A, B)
    maps[mode] = S_AB
    print(f"{mode:<10s} → coherence map computed (shape={S_AB.shape})")

# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for ax, mode in zip(axes, modes):
    im = ax.imshow(maps[mode],
                   extent=[kx.min(), kx.max(), f.min(), f.max()],
                   aspect="auto", origin="lower", cmap="plasma")
    ax.set_title(mode)
    ax.set_xlabel("Spatial freq k (π-domain)")
    ax.set_ylabel("Temporal freq f")
    fig.colorbar(im, ax=ax, shrink=0.7)
fig.suptitle("Test 6B — Spectral Correlation Matrix $S_{AB}(k,f)$")
plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test6B_SpectralMatrix.png", dpi=300)
print("✅ Saved figure to docs/theory/figures/PAEV_Test6B_SpectralMatrix.png")

# ---------------------------------------------------------------------
# Quantitative summary (spectral energy localization)
# ---------------------------------------------------------------------
def spectral_localization(S):
    total = np.sum(S)
    center = np.sum(np.abs(kx)[:,None] * np.sum(S, axis=0)) / total
    spread = np.sqrt(np.sum((np.abs(kx)[:,None]**2) * np.sum(S, axis=0)) / total)
    return center, spread

summary = {}
for mode in modes:
    c, s = spectral_localization(maps[mode])
    summary[mode] = (c, s)
    print(f"{mode:<10s} → center={c:.3f}, spread={s:.3f}")

table_path = "docs/theory/tables/PAEV_Test6B_SpectralMatrix.csv"
with open(table_path, "w") as f:
    f.write("mode,center,spread\n")
    for m, (c, s) in summary.items():
        f.write(f"{m},{c:.6f},{s:.6f}\n")
print(f"✅ Saved table to {table_path}")
print("🏁 PAEV Test 6B complete.")