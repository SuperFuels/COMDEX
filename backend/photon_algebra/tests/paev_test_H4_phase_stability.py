# -*- coding: utf-8 -*-
"""
H4 - Phase Stability & Coherence Test
-------------------------------------
Objective:
  Test whether informational phase coherence persists under weak perturbations.
  Reuses cyclic dataset structure (F7b baseline).

Outputs:
  * PAEV_H4_PhaseCoherence.png
  * backend/modules/knowledge/H4_phase_stability.json
"""
from pathlib import Path
from datetime import datetime, timezone
import json, numpy as np, matplotlib.pyplot as plt

ħ, G, α = 1e-3, 1e-5, 0.5
T, dt = 2400, 0.006
t = np.arange(T) * dt

# Synthetic cyclic phase system (similar to F7b oscillations)
phase1 = np.sin(0.05*t)
phase2 = np.sin(0.05*t + 0.1 + 0.005*np.random.randn(T))

# Coherence: C(t) = <ψ_i ψ_j*>
C = np.cos(phase1 - phase2)
C_mean = np.mean(C[-300:])
C_std = np.std(C[-300:])
stable = C_std < 1e-2 and C_mean > 0.95
classification = "✅ Persistent coherence (informational memory preserved)" if stable else "⚠️ Coherence decay detected"

print("=== H4 - Phase Stability & Coherence Test ===")
print(f"C_mean={C_mean:.4f}, C_std={C_std:.4e}")
print(f"-> {classification}")

plt.figure(figsize=(10,4))
plt.plot(t, C, lw=1.4, label="C(t)")
plt.title("H4 - Informational Phase Coherence")
plt.xlabel("time"); plt.ylabel("C(t)")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_H4_PhaseCoherence.png", dpi=160)
print("✅ Plot saved: PAEV_H4_PhaseCoherence.png")

summary = {
    "ħ": ħ, "G": G, "α": α,
    "metrics": {"C_mean": float(C_mean), "C_std": float(C_std)},
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
Path("backend/modules/knowledge/H4_phase_stability.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved -> backend/modules/knowledge/H4_phase_stability.json")