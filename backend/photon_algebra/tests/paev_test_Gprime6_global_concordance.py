#!/usr/bin/env python3
"""
Test G′6 — Global Concordance Report
Aggregates α′, ħ′, m′, G′ effective constants into a unified coherence map.
"""

import numpy as np, matplotlib.pyplot as plt, json, csv, time

# --- Reference physical constants ---
REFS = {
    "alpha": 7.2973525693e-3,
    "hbar": 1.054571817e-34,
    "m_e": 9.1093837015e-31,
    "G": 6.67430e-11
}

# --- Load latest effective constants from prior stages ---
# (for now, insert directly or load dynamically from results files)
EFFS = {
    "alpha": 7.32e-3,      # from G′2
    "hbar": 1.06e-34,      # from G′3
    "m_e": 9.12e-31,       # from G′4
    "G": 4.26e-11          # from G′5
}

start = time.time()

# --- Compute deviations ---
records = []
for key in EFFS:
    ref = REFS[key]
    eff = EFFS[key]
    dev = 100 * (eff - ref) / ref
    records.append([key, eff, ref, dev])

# --- Concordance Index ---
devs = [r[3] for r in records]
index = np.sqrt(np.mean(np.square(devs)))

# --- Save CSV ---
with open("results_Gprime6_global_concordance.csv","w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Constant","Effective","Reference","Deviation_%"])
    writer.writerows(records)
    writer.writerow([])
    writer.writerow(["Concordance Index", index])

# --- Radar Plot ---
labels = [r[0] for r in records]
stats = [abs(r[3]) for r in records]
angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
stats += stats[:1]
angles += angles[:1]

plt.figure(figsize=(6,6))
ax = plt.subplot(111, polar=True)
ax.plot(angles, stats, 'r-', lw=2)
ax.fill(angles, stats, 'r', alpha=0.2)
ax.set_thetagrids(np.degrees(angles[:-1]), labels)
ax.set_title("G′6 — Global Concordance Radar Map", va='bottom')
ax.set_rlabel_position(0)
plt.tight_layout()
plt.savefig("PAEV_TestGprime6_GlobalConcordance.png")

end = time.time()

# --- Report ---
print("=== G′6 — Global Concordance Summary ===")
for r in records:
    print(f"{r[0]:>5s} : Δ{r[3]:8.3f}%  (Eff={r[1]:.3e}, Ref={r[2]:.3e})")
print(f"\nConcordance Index = {index:.3f} %")
print(f"⏱ Runtime: {end-start:.2f}s")
print(f"\n✅ Saved radar plot: PAEV_TestGprime6_GlobalConcordance.png")
print(f"📄 Saved data: results_Gprime6_global_concordance.csv")