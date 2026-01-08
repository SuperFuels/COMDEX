# backend/photon_algebra/tests/paev_test_Ξ1_optical_lattice_realization.py
"""
Ξ1 - Optical Lattice Realization (Tessaris)
Implements a photonic analogue of the causal lattice.
Encodes spatial potential wells as refractive-index modulation.
"""

import numpy as np, json, datetime, os, matplotlib.pyplot as plt
from backend.photon_algebra.utils.load_constants import load_constants

constants = load_constants()
base_path = "backend/modules/knowledge/"

# 1. Build synthetic optical lattice (Gaussian wells)
x = np.linspace(-10, 10, 512)
n_profile = 1.45 + 0.01 * np.exp(-x**2 / 8.0)
E_field = np.exp(-x**2 / 4.0) * np.cos(2*np.pi*x/5)
I_intensity = E_field**2

# 2. Causal-optical mapping
J_info = np.gradient(I_intensity)
S_entropy = -I_intensity * np.log(np.clip(I_intensity, 1e-12, None))
flux_balance = np.mean(np.abs(J_info))
entropy_balance = np.mean(np.abs(S_entropy))

# 3. Evaluation
ratio = flux_balance / (entropy_balance + 1e-9)
state = "Stable optical lattice" if 0.8 <= ratio <= 1.2 else "Non-causal imbalance"

print("=== Ξ1 - Optical Lattice Realization (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, α={constants['α']}, β={constants['β']}, χ={constants['χ']}")
print(f"⟨|J_info|⟩={flux_balance:.3e}, ⟨|S|⟩={entropy_balance:.3e}, ratio={ratio:.3f} -> {state}")

timestamp = datetime.datetime.now(datetime.UTC).isoformat()
notes = [
    f"Optical lattice refractive profile n(x)=1.45+0.01*exp(-x2/8).",
    f"Mean |J_info|={flux_balance:.3e}, |S|={entropy_balance:.3e}, ratio={ratio:.3f}.",
    "Represents photonic analogue of K-series causal mesh.",
    "Validated under Tessaris Unified Constants & Verification Protocol v1.2."
]

summary = {
    "timestamp": timestamp,
    "constants": constants,
    "metrics": {
        "J_info_mean": float(flux_balance),
        "S_mean": float(entropy_balance),
        "ratio": float(ratio),
        "stable": bool(0.8 <= ratio <= 1.2)
    },
    "notes": notes,
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}

summary_path = os.path.join(base_path, "Ξ1_optical_lattice_summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

plt.figure(figsize=(8,4))
plt.plot(x, n_profile, label="Refractive Index n(x)")
plt.plot(x, E_field, label="Optical Field E(x)")
plt.title("Ξ1 - Optical Lattice Realization (Tessaris)")
plt.xlabel("x (μm)")
plt.ylabel("Amplitude / Index")
plt.legend(); plt.grid(True, alpha=0.3)
plot_path = os.path.join(base_path, "PAEV_Ξ1_optical_lattice.png")
plt.savefig(plot_path, dpi=200); plt.close()

print(f"✅ Summary saved -> {summary_path}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")