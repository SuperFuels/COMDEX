#!/usr/bin/env python3
"""
Test G′3 - Exponent Optimization for Parameter-Free Prediction
Searches Λ-scaling exponents (mass_exp, hbar_exp, G_exp)
to minimize deviation of emergent constants vs. physical constants.
"""

import numpy as np, json, csv, matplotlib.pyplot as plt, itertools, time

# --- Load reference scale factor (from G′1) ---
cfg = json.load(open("backend/photon_algebra/config_physics_scale.json"))
SCALE = cfg["scale_factor"]
REF = f"Lambda (scale_factor = {SCALE:.3e})"

# --- Emergent normalized constants (from G2-G5 results) ---
ALPHA_EMERGENT = 7.23e-3
M_NORM = 4.19e-1
HBAR_NORM = 9.27e-1
G_NORM = 3.60e-2

# --- Physical constants (targets) ---
PLANCK_MASS = 2.176e-8        # kg
PLANCK_HBAR = 1.055e-34       # J*s
PLANCK_G = 6.6743e-11
ALPHA_PHYS = 7.297e-3
M_PHYS = 9.109e-31            # electron
TARGETS = dict(alpha=ALPHA_PHYS, m=M_PHYS, hbar=PLANCK_HBAR, G=PLANCK_G)

# --- Evaluate given exponents ---
def eval_constants(m_exp, hbar_exp, G_exp):
    meff = M_NORM * PLANCK_MASS * SCALE ** m_exp
    hbar_eff = HBAR_NORM * PLANCK_HBAR * SCALE ** hbar_exp
    G_eff = G_NORM * PLANCK_G * SCALE ** G_exp
    devs = dict(
        alpha=100*(ALPHA_EMERGENT-ALPHA_PHYS)/ALPHA_PHYS,
        m=100*(meff-M_PHYS)/M_PHYS,
        hbar=100*(hbar_eff-PLANCK_HBAR)/PLANCK_HBAR,
        G=100*(G_eff-PLANCK_G)/PLANCK_G,
    )
    score = np.mean(np.abs([devs["m"], devs["hbar"], devs["G"]]))
    return devs, score, (meff, hbar_eff, G_eff)

# --- Sweep parameter space ---
m_exp_range = np.linspace(0.2, 1.0, 20)
hbar_exp_range = np.linspace(-1.0, 0.0, 20)
G_exp_range = np.linspace(0.2, 1.0, 20)

best = None
records = []

start = time.time()
for m_exp, hbar_exp, G_exp in itertools.product(m_exp_range, hbar_exp_range, G_exp_range):
    devs, score, vals = eval_constants(m_exp, hbar_exp, G_exp)
    records.append([m_exp, hbar_exp, G_exp, score])
    if (best is None) or (score < best["score"]):
        best = dict(m_exp=m_exp, hbar_exp=hbar_exp, G_exp=G_exp,
                    score=score, devs=devs, vals=vals)
end = time.time()

# --- Save results ---
out_csv = "results_Gprime3_scan.csv"
with open(out_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["m_exp","hbar_exp","G_exp","score"])
    writer.writerows(records)

# --- Plot score landscape (m_exp vs hbar_exp at best G_exp) ---
scores = np.array(records)
mask = np.isclose(scores[:,2], best["G_exp"])
subset = scores[mask]
plt.figure(figsize=(7,5))
plt.tricontourf(subset[:,0], subset[:,1], subset[:,3], levels=30, cmap="plasma")
plt.colorbar(label="Mean |Deviation| %")
plt.scatter(best["m_exp"], best["hbar_exp"], c="white", s=80, edgecolor="k", label="Best")
plt.title(f"G′3 - Scaling Exponent Optimization\n(reference: {REF})")
plt.xlabel("mass exponent")
plt.ylabel("ħ exponent")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestGprime3_ExponentMap.png")

# --- Display best fit summary ---
print("=== G′3 - Exponent Optimization Results ===")
print(f"Reference scaling : {REF}")
print(f"Search space size : {len(records)} combos")
print(f"Best-fit exponents:")
print(f"  mass_exp  = {best['m_exp']:.3f}")
print(f"  hbar_exp  = {best['hbar_exp']:.3f}")
print(f"  G_exp     = {best['G_exp']:.3f}")
print(f"Mean |Deviation| = {best['score']:.3e} %")
print("--- Individual deviations ---")
for k,v in best["devs"].items():
    print(f"{k:>6s}: {v: .3e} %")
print(f"\n✅ Saved plot: PAEV_TestGprime3_ExponentMap.png")
print(f"📄 Saved data: {out_csv}")
print(f"⏱ Runtime: {end-start:.2f}s")