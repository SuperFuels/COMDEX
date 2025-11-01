# -*- coding: utf-8 -*-
"""
H5 - Self-Observation Closure Test (Registry-Compliant Edition)
---------------------------------------------------------------
Goal:
  Couple an observer field O(t) that references its past state via delayed feedback,
  evaluating recursion stability (no divergence).

Outputs:
  * H5_SelfObservation.png
  * backend/modules/knowledge/H5_self_observation.json
"""

from pathlib import Path
from datetime import datetime, timezone
import numpy as np, json, matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# 1) Constants - Tessaris unified registry loader
# ---------------------------------------------------------------------
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ0, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# ---------------------------------------------------------------------
# 2) Define delayed feedback system
# ---------------------------------------------------------------------
T, dt, τ = 2400, 0.006, 20
O = np.zeros(T)
S = 0.7 + 0.05 * np.sin(0.02 * np.arange(T))
E = 0.1 * np.cos(0.01 * np.arange(T))

for k in range(τ, T):
    feedback = 0.8 * O[k - τ] + 0.2 * S[k] - 0.1 * E[k]
    O[k] = np.tanh(feedback)

# ---------------------------------------------------------------------
# 3) Stability metrics
# ---------------------------------------------------------------------
O_std = np.std(O[-600:])
O_mean = np.mean(O[-600:])
stable = O_std < 0.05
classification = (
    "✅ Recursive self-observation stable"
    if stable
    else "⚠️ Recursion instability detected"
)

# ---------------------------------------------------------------------
# 4) Plot
# ---------------------------------------------------------------------
plt.figure(figsize=(10, 4))
plt.plot(O, lw=1.5, label="O(t)")
plt.title("H5 - Self-Observation Closure Test")
plt.xlabel("Time")
plt.ylabel("Observer Field O(t)")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("H5_SelfObservation.png", dpi=150)
plt.close()

print("=== H5 - Self-Observation Closure ===")
print(f"ħ={ħ:.1e}, G={G:.1e}, α={α:.2f}, Λ0={Λ0:.1e}, β={β:.2f}")
print(f"O_mean={O_mean:.4f}, σ={O_std:.4f}")
print(f"-> {classification}")
print("✅ Plot saved: H5_SelfObservation.png")

# ---------------------------------------------------------------------
# 5) Knowledge card export
# ---------------------------------------------------------------------
summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α": α,
    "β": β,
    "τ": τ,
    "metrics": {"O_mean": float(O_mean), "O_std": float(O_std)},
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}

out_path = Path("backend/modules/knowledge/H5_self_observation.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved -> {out_path}")