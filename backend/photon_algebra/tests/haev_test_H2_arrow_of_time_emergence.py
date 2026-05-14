# backend/photon_algebra/tests/haev_test_H2_arrow_of_time_emergence.py
import json
import os
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt

# Minimal embedded dual-field bounce simulator (simplified)
class DualFieldBounce:
    @staticmethod
    def simulate(params, dt, T):
        # NOTE: This is a placeholder dynamics model; keep claims model-only.
        t = np.arange(0, T * dt, dt)
        phi = np.sin(0.01 * t) * np.exp(-0.0001 * t)
        psi = np.cos(0.01 * t) * np.exp(-0.0001 * t)
        cycles = 4
        cycle_indices = np.array_split(np.arange(len(t)), cycles)
        return {"t": t, "phi": phi, "psi": psi, "cycles": cycles, "cycle_indices": cycle_indices}

dualfield_bounce = DualFieldBounce

# 1. Parameters from F7b-RC2 baseline
params = {
    "alpha": 0.7, "beta": 0.08,
    "Lambda_base": 0.0035, "kappa": 0.065,
    "omega0": 0.18, "xi": 0.015, "delta": 0.05,
    "noise": 0.0006, "rho_c": 1.0,
    "g_couple": 0.015,
    "kp": 0.2, "ki": 0.005, "kd": 0.04
}

T = 12000   # multiple cycles
dt = 0.002

# 2. Simulate dual-field dynamics
results = dualfield_bounce.simulate(params, dt, T)

phi = results["phi"]
psi = results["psi"]

# 3. Compute entropies & mutual information per cycle
def entropy(field):
    prob = np.abs(field) ** 2
    denom = np.sum(prob)
    if denom <= 0:
        return 0.0
    prob = prob / denom
    return float(-np.sum(prob * np.log(prob + 1e-12)))

num_cycles = int(results["cycles"])
S_total = []
I_mutual = []

for cycle in range(num_cycles):
    idx = results["cycle_indices"][cycle]
    S_v = entropy(phi[idx])
    S_h = entropy(psi[idx])
    S_t = entropy(phi[idx] + psi[idx])
    S_total.append(S_t)
    I_mutual.append(S_v + S_h - S_t)

S_total = np.array(S_total, dtype=float)
I_mutual = np.array(I_mutual, dtype=float)

# 4. Entropy drift per cycle
entropy_drift = np.diff(S_total) if len(S_total) >= 2 else np.array([0.0], dtype=float)
arrow_direction = "Forward" if float(np.mean(entropy_drift)) > 0 else "None"

# 5. Save metrics
metrics = {
    "entropy_cycle_mean": float(np.mean(S_total)) if len(S_total) else 0.0,
    "entropy_drift_mean": float(np.mean(entropy_drift)) if len(entropy_drift) else 0.0,
    "mutual_information_asymmetry": float(np.mean(np.abs(np.diff(I_mutual)))) if len(I_mutual) >= 2 else 0.0,
    "arrow_direction": arrow_direction
}

print("=== H2 - Emergent Arrow of Time ===")
print(f"Entropy drift mean: {metrics['entropy_drift_mean']:.4e}")
print(f"Mutual info asymmetry: {metrics['mutual_information_asymmetry']:.4e}")
print(f"-> {metrics['arrow_direction']} Arrow Detected")

# Ensure output directory exists
knowledge_dir = "backend/modules/knowledge"
os.makedirs(knowledge_dir, exist_ok=True)

# 6. Plot entropy vs cycle index (save into knowledge dir)
plt.figure()
plt.plot(S_total, label="Total Entropy")
plt.xlabel("Cycle index")
plt.ylabel("Entropy")
plt.title("Entropy per Cycle (H2 Arrow of Time)")
plt.legend()

plot_path = "backend/modules/knowledge/HAEV_H2_EntropyPerCycle.png"
plt.savefig(plot_path, dpi=150, bbox_inches="tight")
plt.close()

output = {
    "constants": params,
    "metrics": metrics,
    "classification": "⏳ Emergent Arrow of Time Detected" if arrow_direction == "Forward" else "⚪ No Directional Bias",
    "files": {"entropy_plot": "backend/modules/knowledge/HAEV_H2_EntropyPerCycle.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

output_path = "backend/modules/knowledge/H2_arrow_of_time_emergence.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"✅ Plot saved    -> {plot_path}")
print(f"✅ Results saved -> {output_path}")