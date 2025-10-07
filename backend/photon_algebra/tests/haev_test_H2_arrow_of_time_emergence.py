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
time = results["t"]

# 3. Compute entropies & mutual information per cycle
def entropy(field):
    prob = np.abs(field)**2 / np.sum(np.abs(field)**2)
    return -np.sum(prob * np.log(prob + 1e-12))

num_cycles = results["cycles"]
S_visible, S_hidden, S_total, I_mutual = [], [], [], []

for cycle in range(num_cycles):
    idx = results["cycle_indices"][cycle]
    S_v = entropy(phi[idx])
    S_h = entropy(psi[idx])
    S_t = entropy(phi[idx] + psi[idx])
    S_visible.append(S_v)
    S_hidden.append(S_h)
    S_total.append(S_t)
    I_mutual.append(S_v + S_h - S_t)

S_visible = np.array(S_visible)
S_hidden = np.array(S_hidden)
S_total = np.array(S_total)
I_mutual = np.array(I_mutual)

# 4. Entropy drift per cycle
entropy_drift = np.diff(S_total)
arrow_direction = "Forward" if np.mean(entropy_drift) > 0 else "None"

# 5. Save metrics
metrics = {
    "entropy_cycle_mean": float(np.mean(S_total)),
    "entropy_drift_mean": float(np.mean(entropy_drift)),
    "mutual_information_asymmetry": float(np.mean(np.abs(np.diff(I_mutual)))),
    "arrow_direction": arrow_direction
}

print("=== H2 — Emergent Arrow of Time ===")
print(f"Entropy drift mean: {metrics['entropy_drift_mean']:.4e}")
print(f"Mutual info asymmetry: {metrics['mutual_information_asymmetry']:.4e}")
print(f"→ {metrics['arrow_direction']} Arrow Detected")

# 6. Plot entropy vs cycle index
plt.figure()
plt.plot(S_total, label="Total Entropy")
plt.xlabel("Cycle index")
plt.ylabel("Entropy")
plt.title("Entropy per Cycle (H2 Arrow of Time)")
plt.legend()
plt.savefig("HAEV_H2_EntropyPerCycle.png")

output = {
    "constants": params,
    "metrics": metrics,
    "classification": "⏳ Emergent Arrow of Time Detected" if arrow_direction == "Forward" else "⚪ No Directional Bias",
    "files": {
        "entropy_plot": "HAEV_H2_EntropyPerCycle.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

output_path = "backend/modules/knowledge/H2_arrow_of_time_emergence.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"✅ Results saved → {output_path}")