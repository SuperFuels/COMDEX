#!/usr/bin/env python3
"""
Test I — Informational Universality (Diffusive–Ballistic Crossover)
Part of Tessaris Photon Algebra Framework
"""
import numpy as np, matplotlib.pyplot as plt, json
from datetime import datetime, timezone

# Simulation parameters
N = 256
L = 10.0
x = np.linspace(-L/2, L/2, N)
dx = x[1] - x[0]
dt = 0.002
steps = 600

# Field initialization
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
        psi += dt * (0.2 * lap - 0.01 * psi + 1j * kappa * psi)
        p = np.abs(psi)**2
        cm = np.sum(x * p) / np.sum(p)
        positions.append(cm)
    positions = np.array(positions)
    msd = np.mean((positions - positions[0])**2)
    msd_all[round(v,3)] = float(msd)
    print(f"κ variance={v:.3f} → MSD={msd:.6f}")

# Plot MSD vs kappa variance
plt.figure(figsize=(6,4))
plt.plot(list(msd_all.keys()), list(msd_all.values()), 'o-', lw=2)
plt.xlabel("κ variance")
plt.ylabel("Mean Squared Displacement (MSD)")
plt.title("Test I — Diffusive–Ballistic Crossover")
plt.grid(True, which='both', ls='--', alpha=0.4)
plt.tight_layout()
plt.savefig("PAEV_TestI_MSD.png", dpi=150)

# Classification logic
v_keys = list(msd_all.keys())
v_vals = np.array(list(msd_all.values()))
trend = np.polyfit(v_keys, np.log(v_vals+1e-12), 1)[0]
if trend > 10:
    cls = "Ballistic-dominated regime"
elif trend > 2:
    cls = "Super-diffusive crossover regime"
else:
    cls = "Diffusive regime"

# Output JSON
out = dict(
    parameters=dict(N=N, L=L, steps=steps, dt=dt, dx=dx),
    msd_all=msd_all,
    classification=cls,
    slope_estimate=float(trend),
    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    files=dict(msd_plot="PAEV_TestI_MSD.png")
)
json.dump(out, open("backend/modules/knowledge/I_universality.json", "w"), indent=2)

print(f"→ ✅ Results saved → backend/modules/knowledge/I_universality.json")
print(json.dumps(out, indent=2))