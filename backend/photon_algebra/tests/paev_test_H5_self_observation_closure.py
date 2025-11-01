# -*- coding: utf-8 -*-
"""
H5 - Self-Observation Closure Test
----------------------------------
Objective:
  Introduce recursion through an observer field O(t) that depends on its own delayed output.
  Check for recursive stability and bounded evolution.

Outputs:
  * PAEV_H5_SelfObservation.png
  * backend/modules/knowledge/H5_self_observation_closure.json
"""
from pathlib import Path
from datetime import datetime, timezone
import json, numpy as np, matplotlib.pyplot as plt

ħ, G, α = 1e-3, 1e-5, 0.5
T, dt = 2400, 0.006
t = np.arange(T) * dt

# Simulated entropy & energy drivers
S = 0.70 + 0.05*np.sin(0.12*t)
E = 0.10*np.cos(0.08*t)

# Observer field with delayed recursion
τ = 25  # delay steps (~0.15s)
O = np.zeros(T)
for k in range(1, T):
    delay = max(0, k - τ)
    feedback = np.tanh(0.8 * O[delay] + 0.3*S[k] - 0.2*E[k])
    O[k] = O[k-1] + dt*(-0.04*O[k-1] + feedback)

O_std, O_mean = np.std(O[-300:]), np.mean(O[-300:])
stable = O_std < 0.02 and abs(O_mean) < 0.1
classification = "✅ Stable recursion (self-observation closure achieved)" if stable else "⚠️ Recursive divergence detected"

print("=== H5 - Self-Observation Closure Test ===")
print(f"O_mean={O_mean:.4e}, O_std={O_std:.4e}")
print(f"-> {classification}")

plt.figure(figsize=(10,4))
plt.plot(t, O, lw=1.4)
plt.title("H5 - Self-Observation Recursion Dynamics")
plt.xlabel("time"); plt.ylabel("O(t)")
plt.tight_layout(); plt.savefig("PAEV_H5_SelfObservation.png", dpi=160)
print("✅ Plot saved: PAEV_H5_SelfObservation.png")

summary = {
    "ħ": ħ, "G": G, "α": α,
    "metrics": {"O_mean": float(O_mean), "O_std": float(O_std)},
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
Path("backend/modules/knowledge/H5_self_observation_closure.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved -> backend/modules/knowledge/H5_self_observation_closure.json")