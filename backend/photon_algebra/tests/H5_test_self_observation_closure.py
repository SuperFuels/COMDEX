# -*- coding: utf-8 -*-
"""
H5 — Self-Observation Closure Test
----------------------------------
Goal: Couple an observer field O(t) that references its past state via delayed feedback,
evaluating recursion stability (no divergence).

Outputs:
  • H5_SelfObservation.png
  • backend/modules/knowledge/H5_self_observation.json
"""
from pathlib import Path
from datetime import datetime, timezone
import numpy as np, json, matplotlib.pyplot as plt

# Load constants
CANDIDATES = [Path("backend/modules/knowledge/constants_v1.2.json")]
for p in CANDIDATES:
    if p.exists(): constants = json.loads(p.read_text()); break
else: constants = {}

ħ = float(constants.get("ħ", 1e-3))
α = float(constants.get("α", 0.5))
Λ0 = float(constants.get("Λ", 1e-6))

# Define delayed feedback system
T, dt, τ = 2400, 0.006, 20
O = np.zeros(T)
S = 0.7 + 0.05*np.sin(0.02*np.arange(T))
E = 0.1*np.cos(0.01*np.arange(T))

for k in range(τ, T):
    feedback = 0.8 * O[k-τ] + 0.2*S[k] - 0.1*E[k]
    O[k] = np.tanh(feedback)

O_std = np.std(O[-600:])
O_mean = np.mean(O[-600:])
stable = O_std < 0.05
classification = "✅ Recursive self-observation stable" if stable else "⚠️ Recursion instability detected"

# Plot
plt.figure(figsize=(10,4))
plt.plot(O, lw=1.5, label="O(t)")
plt.title("H5 — Self-Observation Closure Test")
plt.xlabel("time"); plt.ylabel("Observer Field O(t)")
plt.legend(); plt.tight_layout()
plt.savefig("H5_SelfObservation.png", dpi=150)

print("=== H5 — Self-Observation Closure ===")
print(f"ħ={ħ:.1e}, α={α:.2f}, τ={τ}")
print(f"O_mean={O_mean:.4f}, σ={O_std:.4f}")
print(f"→ {classification}")

# Save summary
summary = {
    "ħ": ħ, "α": α, "Λ0": Λ0, "τ": τ,
    "metrics": {"O_mean": float(O_mean), "O_std": float(O_std)},
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
Path("backend/modules/knowledge/H5_self_observation.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/H5_self_observation.json")