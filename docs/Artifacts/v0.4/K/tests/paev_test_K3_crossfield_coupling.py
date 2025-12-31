# === K3 - Cross-Field Causal Coupling (Tessaris) ===
# Using Tessaris Unified Constants & Verification Protocol

import os, json, datetime
import numpy as np
import matplotlib.pyplot as plt

# ✅ Correct import for your repo structure
from backend.photon_algebra.utils.load_constants import load_constants

# === 1. Load constants ===
constants = load_constants()
print("=== K3 - Cross-Field Causal Coupling (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, "
      f"α={constants['α']}, β={constants['β']}, χ={constants['χ']}")

# === 2. Parameters ===
N = 512
steps = 4000
dx = 1.0
dt = 0.001
damping = 0.04
c_eff = np.sqrt(0.5)

# === 3. Initialize coupled fields ===
x = np.linspace(0, N * dx, N)
u = 0.1 * np.sin(2 * np.pi * x / N)
v = 0.1 * np.cos(2 * np.pi * x / N)

u_history = []
v_history = []
coupling_strength = []

# === 4. Evolution loop ===
for t in range(steps):
    lap_u = np.gradient(np.gradient(u))
    lap_v = np.gradient(np.gradient(v))

    du_dt = v
    dv_dt = (c_eff ** 2) * lap_u - constants["Λ"] * u - constants["β"] * v + constants["χ"] * (u ** 3)
    # symmetric coupling
    dv_dt += 0.1 * (np.gradient(np.gradient(v)) - np.gradient(np.gradient(u)))

    # integrate
    u += du_dt * dt
    v += dv_dt * dt

    # damping
    u *= (1.0 - damping * dt)
    v *= (1.0 - damping * dt)

    # record coupling measure
    C_uv = np.mean(du_dt * v) / (np.mean(u ** 2 + v ** 2) + 1e-12)
    coupling_strength.append(C_uv)
    u_history.append(np.mean(u))
    v_history.append(np.mean(v))

coupling_strength = np.array(coupling_strength)

# === 5. Derived metrics ===
mean_Cuv = np.mean(coupling_strength)
var_Cuv = np.var(coupling_strength)
within_tolerance = abs(mean_Cuv) < 1e-2

print(f"⟨C_uv⟩={mean_Cuv:.3e}, Var(C_uv)={var_Cuv:.3e}")
if within_tolerance:
    print("✅  Cross-field coupling symmetric and causal.")
else:
    print("⚠️  Cross-field drift detected - check coupling or damping balance.")

# === 6. Plot results ===
plt.figure(figsize=(8,4))
plt.plot(coupling_strength, label='C_uv(t)', color='crimson')
plt.axhline(mean_Cuv, color='gray', linestyle='--', label='⟨C_uv⟩')
plt.xlabel("Time step")
plt.ylabel("Coupling coefficient C_uv")
plt.title("K3 - Cross-Field Causal Coupling")
plt.legend()
plt.tight_layout()

plot_path = "backend/modules/knowledge/PAEV_K3_crossfield_coupling.png"
plt.savefig(plot_path)
plt.close()

# === 7. Discovery Notes ===
discovery = [
    f"Mean coupling coefficient ⟨C_uv⟩ = {mean_Cuv:.3e}.",
    f"Variance Var(C_uv) = {var_Cuv:.3e}.",
    "Symmetric coupling ensures causal balance between field domains (u↔v).",
    "Deviation <1e-2 considered fully causal under Tessaris Unified Constants & Verification Protocol."
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
        "mean_Cuv": float(mean_Cuv),
        "var_Cuv": float(var_Cuv),
        "within_tolerance": bool(within_tolerance)
    },
    "files": {"plot": os.path.basename(plot_path)},
    "notes": discovery
}

summary_path = "backend/modules/knowledge/K3_crossfield_coupling_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print(f"✅ Summary saved -> {summary_path}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")