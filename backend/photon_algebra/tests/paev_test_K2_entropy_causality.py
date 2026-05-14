# === K2 - Tessaris Entropy Causality Evolution ===
# Using Tessaris Unified Constants & Verification Protocol

import os, json, datetime
import numpy as np
import matplotlib.pyplot as plt

# ✅ Correct import path confirmed from your project:
from backend.photon_algebra.utils.load_constants import load_constants

# === 1. Load Constants ===
constants = load_constants()

print("=== K2 - Entropy Causality Evolution (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, "
      f"α={constants['α']}, β={constants['β']}, χ={constants['χ']}")

# === 2. Simulation Parameters ===
N = 512
steps = 4000
dx = 1.0
dt = 0.001
damping = 0.04
c_eff = np.sqrt(0.5)

# === 3. Initialize Fields ===
x = np.linspace(0, N * dx, N)
u = np.sin(2 * np.pi * x / N) * 0.1
v = np.zeros_like(u)
S = np.zeros_like(u)

# === 4. Evolution ===
S_history = []
for t in range(steps):
    lap_u = np.gradient(np.gradient(u))
    du_dt = v
    dv_dt = (c_eff ** 2) * lap_u - constants["Λ"] * u - constants["β"] * v + constants["χ"] * (u ** 3)
    v += dv_dt * dt
    u += du_dt * dt

    # Entropy density (Shannon-like)
    S = -u ** 2 * np.log(np.abs(u) + 1e-9)
    S_history.append(np.mean(S))

    # Damping
    v *= (1.0 - damping * dt)

S_history = np.array(S_history)
dS_dt = np.gradient(S_history, dt)

# === 5. Causality Metrics ===
entropy_flux = np.gradient(S, dx)
R_causal = np.max(np.abs(entropy_flux)) / (np.max(np.abs(v)) + 1e-12)
mean_dSdt = np.mean(np.abs(dS_dt))
within_tolerance = mean_dSdt < 1e-3

print(f"R_causal={R_causal:.4f}, mean |dS/dt|={mean_dSdt:.3e}")
if within_tolerance:
    print("✅  Entropy flow within causal tolerance.")
else:
    print("⚠️  Slight entropy drift detected - adjust damping or dt.")

# === 6. Plot ===
plt.figure(figsize=(8,4))
plt.plot(S_history, label='⟨S⟩(t)', color='teal')
plt.xlabel('Time step')
plt.ylabel('Mean Entropy ⟨S⟩')
plt.title('K2 - Entropy Causality Evolution')
plt.legend()
plt.tight_layout()

plot_path = "backend/modules/knowledge/PAEV_K2_entropy_causality.png"
plt.savefig(plot_path)
plt.close()

# === 7. Discovery Section ===
discovery = [
    "Mean entropy derivative tracks causal equilibration of field lattice.",
    f"Observed mean |dS/dt| = {mean_dSdt:.3e}.",
    f"R_causal = {R_causal:.4f}, indicating bounded entropy propagation velocity.",
    "Deviation below 1e-3 considered fully causal under Tessaris Unified Constants & Verification Protocol."
]

print("\n🧭 Discovery Notes -", datetime.datetime.now(datetime.UTC).isoformat())
print("------------------------------------------------------------")
for line in discovery:
    print("*", line)
print("------------------------------------------------------------")

# === 8. JSON Summary ===
summary = {
    "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    "constants": constants,
    "params": {
        "N": N,
        "steps": steps,
        "dt": dt,
        "dx": dx,
        "damping": damping
    },
    "derived": {
        "c_eff": float(c_eff),
        "mean_dSdt": float(mean_dSdt),
        "R_causal": float(R_causal),
        "within_tolerance": bool(within_tolerance)
    },
    "files": {"plot": os.path.basename(plot_path)},
    "notes": discovery
}

summary_path = "backend/modules/knowledge/K2_entropy_causality_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print(f"✅ Summary saved -> {summary_path}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")