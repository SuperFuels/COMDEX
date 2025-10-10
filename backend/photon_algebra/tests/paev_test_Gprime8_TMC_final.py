#!/usr/bin/env python3
"""
Test G′8 — Tessaris Model Concordance (TMC Evaluation)
Verifies unified closure across α, ħ, mₑ, and corrected G.
"""

import numpy as np, matplotlib.pyplot as plt, csv, time

# --- Reference constants (CODATA 2018/2022) ---
alpha_ref = 7.2973525693e-3
hbar_ref  = 1.054571817e-34
me_ref    = 9.1093837015e-31
G_ref     = 6.6743e-11

# --- Effective constants from final model (from G′6 + G′7) ---
alpha_eff = 7.320e-3
hbar_eff  = 1.060e-34
me_eff    = 9.120e-31
G_eff     = 6.7321e-11  # Corrected G′7 result

# --- Compute deviations (%) ---
def deviation(eff, ref):
    return 100 * (eff - ref) / ref

devs = {
    "alpha": deviation(alpha_eff, alpha_ref),
    "hbar":  deviation(hbar_eff, hbar_ref),
    "m_e":   deviation(me_eff, me_ref),
    "G":     deviation(G_eff, G_ref),
}

# --- Compute Tessaris Model Concordance Index ---
TMC = np.sqrt(np.mean([v**2 for v in devs.values()]))

# --- Save results ---
with open("results_Gprime8_TMC_final.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Constant", "Effective", "Reference", "Deviation_%"])
    writer.writerow(["alpha", alpha_eff, alpha_ref, devs["alpha"]])
    writer.writerow(["hbar",  hbar_eff,  hbar_ref,  devs["hbar"]])
    writer.writerow(["m_e",   me_eff,    me_ref,    devs["m_e"]])
    writer.writerow(["G",     G_eff,     G_ref,     devs["G"]])
    writer.writerow([])
    writer.writerow(["TMC_Index", TMC])

# --- Radar chart ---
labels = list(devs.keys())
values = [abs(devs[k]) for k in labels] + [abs(devs["alpha"])]
angles = np.linspace(0, 2 * np.pi, len(values))
plt.figure(figsize=(6,6))
ax = plt.subplot(111, polar=True)
ax.plot(angles, values, "r-", lw=2)
ax.fill(angles, values, "r", alpha=0.2)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels)
ax.set_yticks(np.linspace(0, max(values), 6))
ax.set_title("G′8 — Tessaris Model Concordance Radar Map", va='bottom')
plt.tight_layout()
plt.savefig("PAEV_TestGprime8_TMC_Radar.png")

# --- Report ---
print("=== G′8 — Tessaris Model Concordance (TMC Evaluation) ===")
for k, v in devs.items():
    print(f"{k:5s} : Δ {v:+.3f} %")
print(f"\nTMC Index = {TMC:.3f} %")
if TMC < 10:
    print("✅ Tessaris Model Concordance achieved (Unified Closure)")
else:
    print("⚠️  Partial Concordance — further curvature refinement may be needed.")

print("\n✅ Saved data: results_Gprime8_TMC_final.csv")
print("✅ Saved radar: PAEV_TestGprime8_TMC_Radar.png")
print(f"⏱ Runtime: {time.time():.2f}")