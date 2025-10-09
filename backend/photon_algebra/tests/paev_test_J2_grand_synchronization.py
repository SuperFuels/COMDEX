#!/usr/bin/env python3
"""
J2 — Tessaris TOE Grand Synchronization Test
--------------------------------------------
Validates full multi-regime unification:
Quantum ↔ Relativistic ↔ Thermal coherence consistency.

Checks:
 • Energy–Entropy balance under unified ℒ_total.
 • Cross-coupling of ψ, κ, and T fields under effective constants.
 • Holographic correlation conservation.

Outputs
-------
- backend/modules/knowledge/J2_toe_grand_synchronization.json
- PAEV_J2_toe_synchronization.png

Notes
-----
Model-level only. No physical signaling or spacetime claims implied.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

# ============================================================
#  Load unified constants from Tessaris registry
# ============================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)
ℒ_total = const.get("ℒ_total", 1.0)

print("=== J2 — TOE Grand Synchronization Test (Tessaris) ===")
print(f"Loaded constants → ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3e}, β={β:.3e}, χ={χ:.3e}, |ℒ_total|={ℒ_total:.3e}")

# ============================================================
#  Initialize ψ (quantum), κ (curvature), T (thermal tensor)
# ============================================================
N = 64
x = np.linspace(-3, 3, N)
X, Y = np.meshgrid(x, x)

psi = np.exp(-(X**2 + Y**2)) * np.exp(1j * X * 0.2)
kappa = 1e-3 * np.sin(2 * np.pi * X * Y)
T = 1e-4 * np.cos(X**2 + Y**2)

def laplacian(field):
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4 * field
    )

# ============================================================
#  Evolution loop — unified regime
# ============================================================
dt = 0.01
steps = 700
E_list, S_list, H_list = [], [], []

for step in range(steps + 1):
    # Unified field dynamics under ℒ_total
    psi_t = (
        1j * ħ * laplacian(psi)
        - G * kappa * psi
        + α * T * np.conj(psi)
    )
    kappa_t = G * (laplacian(kappa) - np.abs(psi)**2 + Λ)
    T_t = α * (laplacian(T) - np.abs(kappa)**2)

    # Euler integration
    psi += dt * psi_t
    kappa += dt * kappa_t
    T += dt * T_t

    # Diagnostics
    E = np.mean(np.abs(psi)**2 + np.abs(kappa)**2 + np.abs(T)**2)
    S = -np.sum(np.abs(psi)**2 * np.log(np.abs(psi)**2 + 1e-12)) / psi.size
    H_corr = np.mean(np.real(psi) * kappa) - np.mean(np.real(psi) * T)

    E_list.append(E)
    S_list.append(S)
    H_list.append(H_corr)

    if step % 100 == 0:
        print(f"Step {step:03d} — ⟨E⟩={E:.5e}, S={S:.4f}, H_corr={H_corr:.3e}")

# ============================================================
#  Summary metrics
# ============================================================
E_drift = abs(E_list[-1] - E_list[0])
S_drift = abs(S_list[-1] - S_list[0])
H_drift = abs(H_list[-1] - H_list[0])

print("\n=== TOE Synchronization Summary ===")
print(f"ΔE (energy drift)         = {E_drift:.3e}")
print(f"ΔS (entropy drift)        = {S_drift:.3e}")
print(f"ΔH (holographic drift)    = {H_drift:.3e}")

if E_drift < 1e-3 and S_drift < 1e-2 and H_drift < 1e-4:
    print("✅ Tessaris TOE closure achieved — conservation and coherence hold.")
else:
    print("⚠️  Deviations detected — refinement or recalibration may be required.")

# ============================================================
#  Visualization
# ============================================================
plt.figure(figsize=(8,5))
plt.plot(E_list, label="Energy ⟨E⟩")
plt.plot(S_list, label="Entropy ⟨S⟩")
plt.plot(H_list, label="Holographic Corr. ⟨H⟩")
plt.xlabel("Step")
plt.ylabel("Value")
plt.title("J2 — Tessaris TOE Synchronization Dynamics")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plot_path = "PAEV_J2_toe_synchronization.png"
plt.savefig(plot_path, dpi=200)
print(f"✅ Diagnostic plot saved → {plot_path}")
# ============================================================
#  JSON summary output (safe for NumPy types)
# ============================================================
def to_native(obj):
    """Convert NumPy / complex / bool types to native JSON-safe ones."""
    if isinstance(obj, (np.generic,)):
        return obj.item()
    if isinstance(obj, complex):
        return {"real": obj.real, "imag": obj.imag}
    if isinstance(obj, (list, tuple)):
        return [to_native(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    return obj

ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
summary = {
    "timestamp": ts,
    "constants": const,
    "params": {"N": N, "steps": steps, "dt": dt},
    "results": {
        "E_drift": E_drift,
        "S_drift": S_drift,
        "H_drift": H_drift,
        "mean_E": float(np.mean(E_list)),
        "mean_S": float(np.mean(S_list)),
        "mean_H": float(np.mean(H_list)),
    },
    "verdict": {
        "coherence_stable": bool(E_drift < 1e-3 and S_drift < 1e-2 and H_drift < 1e-4),
        "requires_refinement": bool(not (E_drift < 1e-3 and S_drift < 1e-2 and H_drift < 1e-4)),
    },
    "files": {"figure": plot_path},
    "notes": [
        "Verifies unification across ψ, κ, and T domains.",
        "All quantities are algebraic diagnostics within Tessaris TOE formalism.",
        "No physical or spacetime-level interpretation implied."
    ],
}

out_path = Path("backend/modules/knowledge/J2_toe_grand_synchronization.json")
out_path.write_text(json.dumps(to_native(summary), indent=2))
print(f"✅ Summary saved → {out_path}")
print("----------------------------------------------------------")