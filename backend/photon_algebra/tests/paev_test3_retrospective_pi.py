#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 3π - Retrospective Reconstruction from π-phase sweep
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.visibility import compute_visibility, project_with_pi

RAW_DIR = "data/raw/pi_sweep_frames"
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs("docs/theory/figures", exist_ok=True)
os.makedirs("docs/theory/tables", exist_ok=True)

phases = [1, 2, 4, 8, 16]
print("⚙️ Regenerating π-sweep dataset using project_with_pi kernel...")

# ------------------------------------------------------------
# Construct symbolic-scale multi-frequency interference field
# ------------------------------------------------------------
x = np.linspace(-1, 1, 512)
y = np.linspace(-1, 1, 512)
X, Y = np.meshgrid(x, y)

# Rich fringe spectrum - covers multiple coherence bands
phi1 = 2 * np.pi * 80 * X
phi2 = 2 * np.pi * 140 * X + 0.6 * np.sin(5 * Y)
phi3 = 2 * np.pi * 220 * X + 0.3 * np.cos(7 * Y)
base_field = 0.4 * np.cos(phi1) + 0.3 * np.cos(phi2) + 0.2 * np.cos(phi3)

envelope = 0.6 + 0.4 * np.cos(2 * np.pi * X / 0.4) * np.cos(2 * np.pi * Y / 0.6)
intensity = (0.5 + 0.5 * base_field) * envelope
intensity += 0.05 * np.random.randn(*intensity.shape)
intensity = np.clip(intensity, 0, 1)

# Temporal stack (8 frames with slow phase drift)
base_stack = np.array([
    np.clip(
        (0.5 + 0.5 * np.cos(phi1 + t * 0.25)) *
        (0.6 + 0.3 * np.cos(phi2 + t * 0.4)) +
        0.05 * np.random.randn(*X.shape),
        0, 1
    )
    for t in range(8)
])

# ------------------------------------------------------------
# π projection sweep
# ------------------------------------------------------------
frames, V = [], []
for p in phases:
    projected = project_with_pi(base_stack, pi_spatial=p)
    frames.append(projected)
    np.save(os.path.join(RAW_DIR, f"pi_{p}.npy"), projected)
    v = compute_visibility(projected)
    V.append(v)
    print(f"π_spatial={p:<2d} -> reconstructed V={v:.3f}")

# ------------------------------------------------------------
# Plot and export
# ------------------------------------------------------------
plt.figure(figsize=(6, 4))
plt.plot(phases, V, marker="o", linewidth=2)
plt.xlabel("Spatial phase multiplier π_spatial")
plt.ylabel("Visibility V")
plt.title("Test 3π - Retrospective π-Sweep Reconstruction")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test3_RetroPi.png", dpi=300)
print("✅ Saved figure to docs/theory/figures/PAEV_Test3_RetroPi.png")

np.savetxt(
    "docs/theory/tables/PAEV_Test3_RetroPi.csv",
    np.column_stack([phases, V]),
    delimiter=",",
    header="pi_spatial,visibility",
    fmt="%.4f",
    comments=""
)
print("✅ Saved table to docs/theory/tables/PAEV_Test3_RetroPi.csv")