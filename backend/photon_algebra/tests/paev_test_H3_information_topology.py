# -*- coding: utf-8 -*-
"""
H3 — Information Topology Test
------------------------------
Objective:
  Derive an "information curvature" R_I from entropy or mutual information gradients.
  Confirm whether R_I → 0 at equilibrium, indicating a flat information manifold.

Outputs:
  • PAEV_H3_InfoCurvature.png
  • backend/modules/knowledge/H3_information_topology.json
"""
from pathlib import Path
from datetime import datetime, timezone
import json, numpy as np, matplotlib.pyplot as plt

# ---- Constants (linked to v1.2 registry)
ħ, G, α = 1e-3, 1e-5, 0.5
Λ0 = 1e-6
T, dt = 2400, 0.006
t = np.arange(T) * dt

# Simulated entropy & mutual information dynamics
S = 0.70 + 0.05*np.sin(0.1*t) + 0.02*np.random.randn(T)
I = 0.68 + 0.04*np.cos(0.1*t + 0.5) + 0.01*np.random.randn(T)

# Information curvature proxy:
# R_I = (∂S/∂t * ∂²I/∂t² - ∂I/∂t * ∂²S/∂t²) / (1 + (∂S/∂t)² + (∂I/∂t)²)^(3/2)
dS = np.gradient(S, dt)
dI = np.gradient(I, dt)
d2S = np.gradient(dS, dt)
d2I = np.gradient(dI, dt)
R_I = (dS*d2I - dI*d2S) / (1.0 + dS**2 + dI**2)**1.5

R_mean = np.mean(R_I[-300:])
R_std  = np.std(R_I[-300:])
flat = abs(R_mean) < 1e-3 and R_std < 2e-3
classification = "✅ Flat information manifold (equilibrium achieved)" if flat else "⚠️ Information curvature residuals detected"

# ---- Diagnostics
print("=== H3 — Information Topology Test ===")
print(f"ħ={ħ:.1e}, G={G:.1e}, α={α:.2f}")
print(f"R_I_mean={R_mean:.4e}, R_I_std={R_std:.4e}")
print(f"→ {classification}")

# ---- Plot
plt.figure(figsize=(10,4))
plt.plot(t, R_I, lw=1.4)
plt.title("H3 — Information Curvature Evolution (R_I)")
plt.xlabel("time"); plt.ylabel("R_I")
plt.tight_layout(); plt.savefig("PAEV_H3_InfoCurvature.png", dpi=160)
print("✅ Plot saved: PAEV_H3_InfoCurvature.png")

# ---- Knowledge card
summary = {
    "ħ": ħ, "G": G, "α": α, "Λ0": Λ0,
    "metrics": {"R_I_mean": float(R_mean), "R_I_std": float(R_std)},
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
Path("backend/modules/knowledge/H3_information_topology.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/H3_information_topology.json")