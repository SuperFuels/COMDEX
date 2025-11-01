#!/usr/bin/env python3
"""
Test G′3 - Stability Sweep
Runs prediction under variable noise/grid to check robustness.
"""

import os, numpy as np, pandas as pd, subprocess

NOISES = [0.5, 1.0, 2.0]
GRIDS = [64, 96, 128]

records = []
for n in NOISES:
    for g in GRIDS:
        env = os.environ.copy()
        env["NOISE_LEVEL"] = str(n)
        env["GRID_SIZE"] = str(g)
        subprocess.run(["python","backend/photon_algebra/tests/paev_test_Gprime2_prediction.py"], env=env)
        data = pd.read_csv("results_Gprime2.csv")
        alpha = float(data.iloc[0,1])
        records.append({"noise":n,"grid":g,"alpha":alpha})

df = pd.DataFrame(records)
df.to_csv("results_Gprime3_sweep.csv", index=False)
print("✅ Stability sweep complete. Results saved to results_Gprime3_sweep.csv.")