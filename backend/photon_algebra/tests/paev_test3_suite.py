#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Unified Test 3 Suite - μ / π Stability and Collapse Experiments
---------------------------------------------------------------
Runs all PAEV Test 3 variants:
 - 3μ : Phase noise sweep
 - 3π : Retrospective π-sweep reconstruction
 - 3π-DC : Delayed-choice visibility collapse
 - 3π-TE : Tag + erasure visibility restoration

All results are logged and plotted into a combined summary.
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
print("⚙️ Running unified PAEV Test 3 suite...")

# ================================================================
# TEST 3μ - PHASE NOISE SWEEP
# ================================================================
def test_mu_noise():
    sigmas = [0.0, 0.2, 0.5, 1.0]
    V = []
    x = np.linspace(-np.pi, np.pi, 256)
    slit1 = np.sin(5 * x)
    for s in sigmas:
        phase_noise = np.random.normal(0, s, size=x.shape)
        slit2 = np.sin(5 * x + phase_noise)
        intensity = (slit1 + slit2) ** 2
        intensity /= np.max(intensity)
        V.append(compute_visibility(intensity))
    return np.array(sigmas), np.array(V)

# ================================================================
# TEST 3π - RETROSPECTIVE π-SWEEP
# ================================================================
def test_pi_sweep():
    phases = [1, 2, 4, 8, 16]
    H = W = 256
    x = np.linspace(-10e-3, 10e-3, W)
    X = np.tile(x, (H, 1))
    base_stack = np.array([0.5 + 0.5 * np.cos(2 * np.pi * 48 * X + t * 0.2) for t in range(8)])
    V = []
    for p in phases:
        proj = project_with_pi(base_stack, pi_spatial=p)
        V.append(compute_visibility(proj))
    return np.array(phases), np.array(V)

# ================================================================
# TEST 3π-DC - DELAYED CHOICE
# ================================================================
def test_delayed_choice():
    H = W = 512
    x = np.linspace(-10e-3, 10e-3, W)
    X = np.tile(x, (H, 1))
    raw = np.array([0.5 + 0.5 * np.cos(2 * np.pi * 96 * X + t * 0.4) for t in range(8)])
    before = project_with_pi(raw, pi_spatial=1)
    after = project_with_pi(raw, pi_spatial=16)
    V_before = compute_visibility(before)
    V_after = compute_visibility(after)
    return np.array([1, 16]), np.array([V_before, V_after])

# ================================================================
# TEST 3π-TE - TAG + ERASER
# ================================================================
def test_tag_eraser():
    W = 1024
    x = np.linspace(-10e-3, 10e-3, W)
    phi = 2 * np.pi * 36 * x
    I_coh = 0.5 + 0.45 * np.cos(phi)
    I_mark = 0.5 + 0.05 * np.cos(phi) + 0.3 * np.random.rand(W)
    I_erase = 0.5 + 0.25 * np.cos(phi)
    return np.array(["baseline", "marker", "eraser"]), np.array([
        compute_visibility(I_coh),
        compute_visibility(I_mark),
        compute_visibility(I_erase)
    ])

# ================================================================
# EXECUTION + AGGREGATION
# ================================================================
print("-> Running 3μ noise sweep...")
sigma, V_mu = test_mu_noise()

print("-> Running 3π sweep...")
pi, V_pi = test_pi_sweep()

print("-> Running 3π delayed choice...")
pi_dc, V_dc = test_delayed_choice()

print("-> Running 3π tag eraser...")
labels_te, V_te = test_tag_eraser()

# ================================================================
# SUMMARY LOG
# ================================================================
print("\n--- SUMMARY ---")
print("3μ noise:       ", dict(zip(sigma, np.round(V_mu, 3))))
print("3π sweep:       ", dict(zip(pi, np.round(V_pi, 3))))
print("3π delayed:     ", dict(zip(pi_dc, np.round(V_dc, 3))))
print("3π tag/eraser:  ", dict(zip(labels_te, np.round(V_te, 3))))

# Save CSV
summary_path = "docs/theory/tables/PAEV_Test3_Summary.csv"
np.savetxt(summary_path,
           np.column_stack([np.arange(len(V_mu)), V_mu]),
           delimiter=",", header="index,V_mu", fmt="%.4f", comments="")
print(f"✅ Saved summary to {summary_path}")

# ================================================================
# VISUALIZATION
# ================================================================
plt.figure(figsize=(10, 6))

plt.subplot(2, 2, 1)
plt.plot(sigma, V_mu, marker="o")
plt.xlabel("Phase noise σ")
plt.ylabel("Visibility V")
plt.title("3μ - Phase Noise Sweep")
plt.grid(True, alpha=0.3)

plt.subplot(2, 2, 2)
plt.plot(pi, V_pi, marker="o")
plt.xlabel("π_spatial")
plt.ylabel("Visibility V")
plt.title("3π - Retrospective Sweep")
plt.grid(True, alpha=0.3)

plt.subplot(2, 2, 3)
plt.bar(["Before", "After"], V_dc, color=["#4caf50", "#e91e63"])
plt.ylabel("Visibility V")
plt.title("3π - Delayed Choice")

plt.subplot(2, 2, 4)
plt.bar(labels_te, V_te, color=["#2196f3", "#ff9800", "#9c27b0"])
plt.ylabel("Visibility V")
plt.title("3π - Tag Eraser")

plt.tight_layout()
plt.savefig("docs/theory/figures/PAEV_Test3_Summary.png", dpi=300)
print("✅ Saved combined figure to docs/theory/figures/PAEV_Test3_Summary.png")
print("🏁 All PAEV Test 3 experiments complete.")