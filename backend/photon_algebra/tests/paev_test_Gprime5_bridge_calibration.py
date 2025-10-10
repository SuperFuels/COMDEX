#!/usr/bin/env python3
"""
Test G′5 — Dimensional Bridge Calibration
Adds curvature ratio bridge Xi^β to rescale G_eff into physical regime.
"""

import numpy as np, json, matplotlib.pyplot as plt, csv, time

# --- Load Λ scaling ---
cfg = json.load(open("backend/photon_algebra/config_physics_scale.json"))
SCALE = cfg["scale_factor"]
REF = f"Lambda (scale_factor = {SCALE:.3e})"

# --- Constants ---
PLANCK_G = 6.6743e-11
PLANCK_HBAR = 1.055e-34
PLANCK_MASS = 2.176e-8
C = 2.99792458e8
LAMBDA = 1e-52   # cosmological constant
G_NORM, G_EXP = 3.60e-2, 0.200

# --- Define curvature ratio ---
Rq = np.sqrt(PLANCK_HBAR * PLANCK_G / C**3)
Rc = np.sqrt(3 / LAMBDA)
Xi = Rq / Rc

# --- Evaluation ---
def compute_G_eff(beta):
    return PLANCK_G * G_NORM * (SCALE**G_EXP) * (Xi**beta)

def deviation(G_eff):
    return 100 * (G_eff - PLANCK_G) / PLANCK_G

# --- Sweep β ---
beta_vals = np.linspace(-2, 6, 800)
records = []
best = None
start = time.time()
for beta in beta_vals:
    G_eff = compute_G_eff(beta)
    dev = deviation(G_eff)
    records.append([beta, dev])
    if (best is None) or (abs(dev) < abs(best["dev"])):
        best = dict(beta=beta, G_eff=G_eff, dev=dev)
end = time.time()

# --- Save data ---
with open("results_Gprime5_bridge_scan.csv","w",newline="") as f:
    csv.writer(f).writerows([["beta","G_dev_%"]] + records)

# --- Plot ---
records = np.array(records)
plt.figure(figsize=(8,5))
plt.plot(records[:,0], records[:,1], 'r-', lw=2)
plt.axhline(0, color='k', ls='--')
plt.axvline(best["beta"], color='b', ls=':')
plt.title("G′5 — Dimensional Bridge Calibration (β Sweep)")
plt.xlabel("β (bridge exponent)")
plt.ylabel("ΔG (%) vs Physical Constant")
plt.tight_layout()
plt.savefig("PAEV_TestGprime5_BridgeSweep.png")

# --- Report ---
print("=== G′5 — Dimensional Bridge Calibration Results ===")
print(f"Reference scaling : {REF}")
print(f"Curvature ratio Xi = {Xi:.3e}")
print(f"Best β : {best['beta']:.3f}")
print(f"G_eff : {best['G_eff']:.3e}")
print(f"ΔG : {best['dev']:.3f} %")
print(f"⏱ Runtime: {end-start:.2f}s")
print(f"\n✅ Saved plot: PAEV_TestGprime5_BridgeSweep.png")
print(f"📄 Saved data: results_Gprime5_bridge_scan.csv")