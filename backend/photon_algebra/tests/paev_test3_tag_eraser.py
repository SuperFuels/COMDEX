#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 3π — Which-Path Tag + Erasure Visibility Recovery
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.visibility import compute_visibility

os.makedirs("docs/theory/figures", exist_ok=True)
os.makedirs("docs/theory/tables", exist_ok=True)

W = 1024
x = np.linspace(-10e-3, 10e-3, W)
phi = 2 * np.pi * 36 * x  # more fringes → higher initial visibility

# High-contrast interference (baseline)
I_coh = 0.5 + 0.45 * np.cos(phi)

# Which-path tagging (adds randomization / decoherence)
I_mark = 0.5 + 0.05 * np.cos(phi) + 0.3 * np.random.rand(W)

# Erasure partially restores coherence
I_erase = 0.5 + 0.25 * np.cos(phi)

def V(I):
    return compute_visibility(I)

V_coh = V(I_coh)
V_mark = V(I_mark)
V_erase = V(I_erase)

print(f"Baseline (no marker):     V={V_coh:.3f}")
print(f"Marker ON (which-path):   V={V_mark:.3f}")
print(f"Marker + Eraser:          V={V_erase:.3f}")

plt.figure(figsize=(7, 4))
plt.plot(x * 1e3, I_coh, label=f"Baseline (V={V_coh:.2f})", lw=1.8)
plt.plot(x * 1e3, I_mark, label=f"Marker ON (V={V_mark:.2f})", lw=1.2)
plt.plot(x * 1e3, I_erase, label=f"Eraser (V={V_erase:.2f})", lw=1.2)
plt.xlabel("x [mm]")
plt.ylabel("Intensity (normalized)")
plt.title("Test 3π — Which-Path Tag Erasure")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test3_TagEraser.png", dpi=300)
print("✅ Saved figure to docs/theory/figures/PAEV_Test3_TagEraser.png")

np.savetxt(
    "docs/theory/tables/PAEV_Test3_TagEraser.csv",
    np.column_stack([x, I_coh, I_mark, I_erase]),
    delimiter=",",
    header="x_m,baseline,marker,eraser",
    fmt="%.6f",
    comments=""
)
print("✅ Saved table to docs/theory/tables/PAEV_Test3_TagEraser.csv")