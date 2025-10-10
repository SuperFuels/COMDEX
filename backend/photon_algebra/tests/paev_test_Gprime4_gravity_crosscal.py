#!/usr/bin/env python3
"""
Test G′4 — Gravitational Cross-Calibration
Refines G scaling by including entropy–curvature feedback.
"""

import numpy as np, json, csv, matplotlib.pyplot as plt, time

# --- Load Λ scaling factor ---
cfg = json.load(open("backend/photon_algebra/config_physics_scale.json"))
SCALE = cfg["scale_factor"]
REF = f"Lambda (scale_factor = {SCALE:.3e})"

# --- Constants from G′3 ---
m_exp, hbar_exp, G_exp = 0.453, 0.000, 0.200
M_NORM, HBAR_NORM, G_NORM = 4.19e-1, 9.27e-1, 3.60e-2
ALPHA_EMERGENT = 7.23e-3

# --- Physical constants ---
PLANCK_MASS = 2.176e-8      # kg
PLANCK_HBAR = 1.055e-34     # J·s
PLANCK_G = 6.6743e-11
ALPHA_PHYS = 7.297e-3
M_PHYS = 9.109e-31
S_ENTROPY = 0.817  # from G5

# --- Function to evaluate deviations given η ---
def eval_eta(eta):
    meff = M_NORM * PLANCK_MASS * SCALE**m_exp
    hbar_eff = HBAR_NORM * PLANCK_HBAR * SCALE**hbar_exp
    G_eff = G_NORM * PLANCK_G * SCALE**G_exp * (1 + eta * S_ENTROPY)
    devs = dict(
        alpha = 100*(ALPHA_EMERGENT - ALPHA_PHYS)/ALPHA_PHYS,
        m = 100*(meff - M_PHYS)/M_PHYS,
        hbar = 100*(hbar_eff - PLANCK_HBAR)/PLANCK_HBAR,
        G = 100*(G_eff - PLANCK_G)/PLANCK_G,
    )
    score = np.mean(np.abs([devs["m"], devs["hbar"], devs["G"]]))
    return devs, score, G_eff

# --- Sweep η range ---
eta_vals = np.linspace(0, 5, 200)
records = []
best = None
start = time.time()
for eta in eta_vals:
    devs, score, G_eff = eval_eta(eta)
    records.append([eta, devs["G"], score])
    if (best is None) or (score < best["score"]):
        best = dict(eta=eta, devs=devs, score=score, G_eff=G_eff)
end = time.time()

# --- Save CSV ---
with open("results_Gprime4_eta_scan.csv","w",newline="") as f:
    csv.writer(f).writerows([["eta","G_dev_%","score"]] + records)

# --- Plot ---
records = np.array(records)
plt.figure(figsize=(7,5))
plt.plot(records[:,0], records[:,1], 'r-', lw=2)
plt.axhline(0, color='k', ls='--')
plt.axvline(best["eta"], color='b', ls=':')
plt.title("G′4 — Gravitational Cross-Calibration (η Sweep)")
plt.xlabel("η (entropy coupling coefficient)")
plt.ylabel("ΔG (%) vs Physical Constant")
plt.tight_layout()
plt.savefig("PAEV_TestGprime4_EtaSweep.png")

# --- Print summary ---
print("=== G′4 — Gravitational Cross-Calibration Results ===")
print(f"Reference scaling : {REF}")
print(f"Best η : {best['eta']:.3f}")
print(f"G_eff : {best['G_eff']:.3e}")
print(f"ΔG : {best['devs']['G']:.3f} %")
print(f"Mean |Deviation| : {best['score']:.3f} %")
for k,v in best['devs'].items():
    print(f"{k:>6s}: {v: .3f} %")
print(f"\n✅ Saved plot: PAEV_TestGprime4_EtaSweep.png")
print(f"📄 Saved data: results_Gprime4_eta_scan.csv")
print(f"⏱ Runtime: {end-start:.2f}s")