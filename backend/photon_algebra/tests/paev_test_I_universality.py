#!/usr/bin/env python3
"""
Test I — Informational Universality (Diffusive–Ballistic Crossover)
Part of Tessaris Photon Algebra Framework
"""

import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime, timezone
from pathlib import Path

# -------------------- constants loader --------------------
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]
χ = const.get("χ", 1.0)  # fallback if χ not yet in registry

# -------------------- simulation parameters --------------------
N = 256
L = 10.0
x = np.linspace(-L / 2, L / 2, N)
dx = x[1] - x[0]
dt = 0.002
steps = 600

# -------------------- field initialization --------------------
psi0 = np.exp(-x**2 * 10)
var_k = [0.0, 0.02, 0.05, 0.08]
msd_all = {}

print("=== Test I — Informational Universality (Diffusive–Ballistic Crossover) ===")

for v in var_k:
    psi = psi0.copy().astype(np.complex128)
    kappa = v * np.random.randn(N)
    positions = []
    for t in range(steps):
        lap = (np.roll(psi, -1) + np.roll(psi, 1) - 2 * psi) / dx**2
        # core evolution step
        psi += dt * (α * lap - Λ * psi + 1j * χ * kappa * psi)
        p = np.abs(psi) ** 2
        cm = np.sum(x * p) / np.sum(p)
        positions.append(cm)
    positions = np.array(positions)
    msd = np.mean((positions - positions[0]) ** 2)
    msd_all[round(v, 3)] = float(msd)
    print(f"κ variance={v:.3f} → MSD={msd:.6f}")

# -------------------- plot MSD vs κ variance --------------------
plt.figure(figsize=(6, 4))
plt.plot(list(msd_all.keys()), list(msd_all.values()), "o-", lw=2)
plt.xlabel("κ variance")
plt.ylabel("Mean Squared Displacement (MSD)")
plt.title("Test I — Diffusive–Ballistic Crossover")
plt.grid(True, which="both", ls="--", alpha=0.4)
plt.tight_layout()
plt.savefig("PAEV_TestI_MSD.png", dpi=150)
print("✅ Figure saved → PAEV_TestI_MSD.png")

# -------------------- classification logic --------------------
v_keys = list(msd_all.keys())
v_vals = np.array(list(msd_all.values()))
trend = np.polyfit(v_keys, np.log(v_vals + 1e-12), 1)[0]

if trend > 10:
    cls = "Ballistic-dominated regime"
elif trend > 2:
    cls = "Super-diffusive crossover regime"
else:
    cls = "Diffusive regime"

# -------------------- JSON output --------------------
out = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "constants": const,
    "parameters": {
        "N": N,
        "L": L,
        "steps": steps,
        "dt": dt,
        "dx": dx,
        "ħ": ħ,
        "Λ": Λ,
        "α": α,
        "β": β,
        "χ": χ,
    },
    "msd_all": msd_all,
    "classification": cls,
    "slope_estimate": float(trend),
    "files": {"msd_plot": "PAEV_TestI_MSD.png"},
}

out_path = Path("backend/modules/knowledge/I_universality.json")
out_path.write_text(json.dumps(out, indent=2))
print(f"✅ Results saved → {out_path}")

# -------------------- summary printout --------------------
print(json.dumps(out, indent=2))