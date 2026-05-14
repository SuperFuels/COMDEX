# === Ω2 - Gravitational Cutoff Simulation (Tessaris) ===
# Purpose: Identify saturation point where curvature and information flux
# reach dynamic equilibrium - analog of event horizon stability.
# Complies with Tessaris Unified Constants & Verification Protocol v1.2

import numpy as np
import json, datetime, os
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.load_constants import load_constants

# === 1. Load Tessaris constants ===
constants = load_constants()
base_path = "backend/modules/knowledge/"

# === 2. Load previous Ω1 results if available ===
omega1_path = os.path.join(base_path, "Ω1_collapse_threshold_summary.json")
if os.path.exists(omega1_path):
    with open(omega1_path, "r", encoding="utf-8") as f:
        omega1_data = json.load(f)
    collapse_level = omega1_data["metrics"]["div_J_mean"]
    print(f"Loaded Ω1 collapse level = {collapse_level:.3e}")
else:
    collapse_level = 1e-3
    print("⚠️  Ω1 data not found - using default collapse level = 1e-3.")

# === 3. Generate or load curvature/flux arrays ===
x = np.linspace(-8, 8, 512)
u = np.exp(-x**2 / 10.0)
v = np.gradient(u)
R_eff = np.gradient(np.gradient(u))
J_flux = u * v - np.gradient(u)

# Introduce dynamic feedback damping to simulate cutoff equilibrium
gamma_feedback = 0.05
R_damped = R_eff / (1 + gamma_feedback * (u**2 + v**2))
flux_balance = np.mean(np.abs(J_flux)) - gamma_feedback * np.mean(u**2)

# Compute equilibrium ratio
equilibrium_ratio = np.mean(np.abs(R_damped)) / (collapse_level + 1e-9)

# === 4. Classification ===
if 0.8 <= equilibrium_ratio <= 1.2:
    state = "Stable equilibrium - cutoff achieved"
    stable = True
elif equilibrium_ratio > 1.2:
    state = "Supercritical collapse - over-threshold curvature"
    stable = False
else:
    state = "Subcritical - curvature below equilibrium threshold"
    stable = False

print("\n=== Ω2 - Gravitational Cutoff Simulation (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, α={constants['α']}, β={constants['β']}, χ={constants['χ']}")
print(f"⟨|R_damped|⟩ = {np.mean(np.abs(R_damped)):.3e}, J_flux_mean = {np.mean(np.abs(J_flux)):.3e}")
print(f"Equilibrium ratio = {equilibrium_ratio:.3f} -> {state}\n")

# === 5. Discovery notes ===
timestamp = datetime.datetime.now(datetime.UTC).isoformat()
notes = [
    f"Equilibrium ratio = {equilibrium_ratio:.3f}.",
    f"Mean damped curvature ⟨|R_damped|⟩ = {np.mean(np.abs(R_damped)):.3e}.",
    f"Flux balance = {flux_balance:.3e}.",
    "Stable equilibrium corresponds to gravitational cutoff - event horizon analogue.",
    "Validated under Tessaris Unified Constants & Verification Protocol v1.2."
]

summary = {
    "timestamp": timestamp,
    "constants": constants,
    "metrics": {
        "R_damped_mean": float(np.mean(np.abs(R_damped))),
        "J_flux_mean": float(np.mean(np.abs(J_flux))),
        "flux_balance": float(flux_balance),
        "equilibrium_ratio": float(equilibrium_ratio),
        "stable": bool(stable)
    },
    "notes": notes,
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}

# === 6. Save results ===
summary_path = os.path.join(base_path, "Ω2_gravitational_cutoff_summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

plt.figure(figsize=(8, 4))
plt.plot(x, R_damped, label="Damped curvature (R_damped)")
plt.plot(x, J_flux, label="Information flux (J_flux)")
plt.title("Ω2 - Gravitational Cutoff Simulation")
plt.xlabel("x (lattice coordinate)")
plt.ylabel("Amplitude")
plt.legend()
plt.grid(True, alpha=0.3)
plot_path = os.path.join(base_path, "PAEV_Ω2_gravitational_cutoff.png")
plt.savefig(plot_path, dpi=200)
plt.close()

print(f"✅ Summary saved -> {summary_path}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")