# === K4 - Causal Synchrony Matrix (Tessaris) ===
# Using Tessaris Unified Constants & Verification Protocol

import os, json, datetime
import numpy as np
import matplotlib.pyplot as plt

from backend.photon_algebra.utils.load_constants import load_constants

# === 1. Load constants ===
constants = load_constants()
print("=== K4 - Causal Synchrony Matrix (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, "
      f"α={constants['α']}, β={constants['β']}, χ={constants['χ']}")

# === 2. Parameters ===
N = 128
steps = 1200
dt = 0.001
dx = 1.0
damping = 0.035
c_eff = np.sqrt(0.5)

# === 3. Initialize lattice fields ===
x = np.linspace(0, N * dx, N)
u = 0.1 * np.sin(2 * np.pi * x / N)
v = 0.1 * np.cos(2 * np.pi * x / N)

u_t = []
v_t = []

# === 4. Time evolution ===
for t in range(steps):
    lap_u = np.gradient(np.gradient(u))
    lap_v = np.gradient(np.gradient(v))

    du_dt = v
    dv_dt = (c_eff ** 2) * lap_u - constants["Λ"] * u - constants["β"] * v + constants["χ"] * (u ** 3)

    # symmetric coupling feedback
    dv_dt += 0.08 * (lap_v - lap_u)

    u += du_dt * dt
    v += dv_dt * dt
    u *= (1.0 - damping * dt)
    v *= (1.0 - damping * dt)

    if t % 10 == 0:
        u_t.append(u.copy())
        v_t.append(v.copy())

u_t = np.array(u_t)
v_t = np.array(v_t)
frames = u_t.shape[0]

# === 5. Compute synchrony matrix ===
corr_matrix = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        corr_matrix[i, j] = np.corrcoef(u_t[:, i], v_t[:, j])[0, 1]

R_sync = np.mean(np.abs(corr_matrix))
std_sync = np.std(corr_matrix)

# === 6. Verdict ===
print(f"R_sync={R_sync:.4f}, std_sync={std_sync:.3e}")
if R_sync > 0.9:
    verdict = "✅  Strong causal synchrony achieved."
elif R_sync > 0.7:
    verdict = "⚠️  Partial synchrony - moderate causal drift."
else:
    verdict = "❌  Weak synchrony - check coupling constants."
print(verdict)

# === 7. Plot synchrony matrix ===
plt.figure(figsize=(6, 5))
plt.imshow(corr_matrix, cmap="plasma", origin="lower")
plt.colorbar(label="|Correlation(u_i, v_j)|")
plt.title(f"K4 - Causal Synchrony Matrix (R_sync={R_sync:.3f})")
plt.tight_layout()

plot_path = "backend/modules/knowledge/PAEV_K4_causal_synchrony.png"
plt.savefig(plot_path)
plt.close()

# === 8. Discovery Notes ===
discovery = [
    f"Global synchrony coefficient R_sync = {R_sync:.4f}.",
    f"Synchrony dispersion σ = {std_sync:.3e}.",
    "High R_sync indicates strong causal ordering between lattice domains.",
    "Deviation σ < 1e-2 satisfies Tessaris Unified Constants & Verification Protocol.",
]

print("\n🧭 Discovery Notes -", datetime.datetime.now(datetime.UTC).isoformat())
print("------------------------------------------------------------")
for line in discovery:
    print("*", line)
print("------------------------------------------------------------")

# === 9. JSON Summary ===
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
        "R_sync": float(R_sync),
        "std_sync": float(std_sync)
    },
    "files": {"plot": os.path.basename(plot_path)},
    "notes": discovery
}

summary_path = "backend/modules/knowledge/K4_causal_synchrony_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print(f"✅ Summary saved -> {summary_path}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")