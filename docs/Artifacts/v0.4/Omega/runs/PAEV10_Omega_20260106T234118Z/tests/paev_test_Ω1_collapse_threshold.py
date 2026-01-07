# === Ω1 - Causal Collapse Threshold (Tessaris) ===
# Implements Tessaris Unified Constants & Verification Protocol
# Purpose: Detect gravitational / informational collapse onset
# Output: Ω1_collapse_threshold_summary.json + PAEV_Ω1_collapse_threshold.png

import numpy as np
import json, datetime, os
import matplotlib.pyplot as plt

# === 1. Load constants ===
from backend.photon_algebra.utils.load_constants import load_constants
constants = load_constants()

# === 2. Load prior lattice state (from M6 / K5) ===
base_path = "backend/modules/knowledge/"
u_path = os.path.join(base_path, "M6_field.npy")
v_path = os.path.join(base_path, "M6_velocity.npy")

if not os.path.exists(u_path) or not os.path.exists(v_path):
    print("⚠️  Warning: M6 field files not found. Using synthetic Gaussian test data.")
    x = np.linspace(-10, 10, 512)
    u = np.exp(-x**2 / 12.0)
    v = np.gradient(u)
else:
    u = np.load(u_path)
    v = np.load(v_path)

# === 3. Derived quantities ===
rho_E = 0.5 * (u**2 + v**2)
S = -u * np.log(np.abs(u) + 1e-9)         # entropy-like measure
grad_S = np.gradient(S)
div_J = np.gradient(rho_E - grad_S)
collapse_index = np.mean(np.abs(div_J))

# === 4. Collapse detection criteria ===
R_eff = np.var(u) - np.var(v)
J_info = rho_E - grad_S
J_flux = np.mean(np.abs(J_info))
collapse_threshold = 1e-3

collapsed = collapse_index > collapse_threshold

# === 5. Discovery log ===
print("\n=== Ω1 - Causal Collapse Threshold (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, α={constants['α']}, β={constants['β']}, χ={constants['χ']}")
print(f"⟨|div J|⟩ = {collapse_index:.3e}, J_flux = {J_flux:.3e}, R_eff = {R_eff:.3e}")
if collapsed:
    print("⚠️  Collapse threshold exceeded - causal closure detected.")
else:
    print("✅  Lattice within causal capacity - no collapse.\n")

# === 6. Discovery notes ===
timestamp = datetime.datetime.now(datetime.UTC).isoformat()
notes = [
    f"Mean divergence of information flux |∇*J| = {collapse_index:.3e}.",
    f"Effective curvature variance R_eff = {R_eff:.3e}.",
    "Collapse condition: |∇*J| > 1e-3 -> onset of causal closure.",
    "Represents quantum-gravitational cutoff in Tessaris lattice dynamics."
]

summary = {
    "timestamp": timestamp,
    "constants": constants,
    "metrics": {
        "div_J_mean": float(collapse_index),
        "R_eff": float(R_eff),
        "J_flux": float(J_flux),
        "threshold": collapse_threshold,
        "collapsed": bool(collapsed)
    },
    "notes": notes,
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}

# === 7. Save results ===
summary_path = os.path.join(base_path, "Ω1_collapse_threshold_summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

plt.figure(figsize=(8,4))
plt.plot(u, label="u-field")
plt.plot(v, label="v-field")
plt.title("Ω1 - Causal Collapse Threshold")
plt.xlabel("Lattice index")
plt.ylabel("Amplitude")
plt.legend()
plt.grid(True, alpha=0.3)
plot_path = os.path.join(base_path, "PAEV_Ω1_collapse_threshold.png")
plt.savefig(plot_path, dpi=200)
plt.close()

print(f"✅ Summary saved -> {summary_path}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")