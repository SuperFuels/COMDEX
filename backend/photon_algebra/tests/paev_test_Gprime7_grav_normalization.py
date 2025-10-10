#!/usr/bin/env python3
"""
Test G′7 — Gravitational Normalization & Cosmometric Closure
Applies curvature compensation exponent δ to refine G magnitude.
"""

import numpy as np, matplotlib.pyplot as plt, csv, time

# --- Constants ---
Xi = 9.333e-62              # curvature ratio from G′5
G_eff = 4.259e-11           # effective gravitational constant from G′5
G_ref = 6.6743e-11          # CODATA reference

# --- Parameter sweep ---
deltas = np.linspace(-0.1, 0.1, 400)
G_corr = G_eff * Xi**(-deltas)
devs = 100 * (G_corr - G_ref) / G_ref

# --- Find best δ ---
idx = np.argmin(np.abs(devs))
best_delta = deltas[idx]
best_dev = devs[idx]
best_G = G_corr[idx]

# --- Save data ---
with open("results_Gprime7_grav_normalization.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["delta", "G_corr", "Deviation_%"])
    for d, Gc, dv in zip(deltas, G_corr, devs):
        writer.writerow([d, Gc, dv])
    writer.writerow([])
    writer.writerow(["Best δ", best_delta])
    writer.writerow(["Best G_corr", best_G])
    writer.writerow(["Deviation_%", best_dev])

# --- Plot ---
plt.figure(figsize=(7,5))
plt.plot(deltas, devs, "r-", lw=2)
plt.axhline(0, color="black", ls="--", lw=1)
plt.axvline(best_delta, color="blue", ls=":")
plt.title("G′7 — Gravitational Normalization (δ Sweep)")
plt.xlabel("δ (curvature compensation exponent)")
plt.ylabel("ΔG (%) vs Physical Constant")
plt.tight_layout()
plt.savefig("PAEV_TestGprime7_NormalizationSweep.png")

# --- Report ---
print("=== G′7 — Gravitational Normalization & Cosmometric Closure ===")
print(f"Reference G_ref = {G_ref:.4e}")
print(f"Curvature ratio Xi = {Xi:.3e}")
print(f"Best δ = {best_delta:.6f}")
print(f"G_corr = {best_G:.4e}")
print(f"ΔG = {best_dev:.3f} %")
print("\n✅ Saved data: results_Gprime7_grav_normalization.csv")
print("✅ Saved plot: PAEV_TestGprime7_NormalizationSweep.png")
print(f"⏱ Runtime: {time.time():.2f}")