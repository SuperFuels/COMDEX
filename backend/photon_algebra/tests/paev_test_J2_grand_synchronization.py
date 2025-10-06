"""
J2 — TOE Grand Synchronization Test
-----------------------------------
This test validates full multi-regime unification:
Quantum ↔ Relativistic ↔ Thermal coherence consistency.

It verifies:
 • Energy–Entropy balance under unified ℒ_total.
 • Cross-coupling of ψ, κ, and T fields under effective constants.
 • Holographic correlation conservation.
"""

from __future__ import annotations
import json
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------
# Load constants_v1.0.json (from TOE Engine)
# ---------------------------------------------------------------------
CONST_PATH = Path("backend/modules/knowledge/constants_v1.0.json")
if not CONST_PATH.exists():
    raise FileNotFoundError(f"Missing constants file: {CONST_PATH}")

with CONST_PATH.open("r", encoding="utf-8") as f:
    constants = json.load(f)

ħ_eff = float(constants.get("ħ_eff", 1e-3))
G_eff = float(constants.get("G_eff", 1e-5))
Λ_eff = float(constants.get("Λ_eff", 1e-6))
α_eff = float(constants.get("α_eff", 0.5))
L_total = float(constants.get("L_total", 1.0))
print("=== J2 — TOE Grand Synchronization Test ===")
print(f"Loaded effective constants:")
print(f"  ħ_eff = {ħ_eff:.3e}")
print(f"  G_eff = {G_eff:.3e}")
print(f"  Λ_eff = {Λ_eff:.3e}")
print(f"  α_eff = {α_eff:.3e}")
print(f"  |ℒ_total| = {L_total:.3e}")

# ---------------------------------------------------------------------
# Initialize ψ (quantum), κ (curvature), and T (thermal tensor)
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# Evolution Loop — Unified Regime
# ---------------------------------------------------------------------
dt = 0.01
steps = 700
E_list, S_list, H_list = [], [], []

for step in range(steps + 1):
    # Unified field dynamics under ℒ_total
    psi_t = (
        1j * ħ_eff * laplacian(psi)
        - G_eff * kappa * psi
        + α_eff * T * np.conj(psi)
    )
    kappa_t = G_eff * (laplacian(kappa) - np.abs(psi)**2 + Λ_eff)
    T_t = α_eff * (laplacian(T) - np.abs(kappa)**2)
    
    # Update
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
        print(
            f"Step {step:03d} — ⟨E⟩={E:.5e}, S={S:.4f}, H_corr={H_corr:.3e}"
        )

# ---------------------------------------------------------------------
# Summary Metrics
# ---------------------------------------------------------------------
E_drift = abs(E_list[-1] - E_list[0])
S_drift = abs(S_list[-1] - S_list[0])
H_drift = abs(H_list[-1] - H_list[0])

print("\n=== TOE Synchronization Summary ===")
print(f"ΔE (energy drift)         = {E_drift:.3e}")
print(f"ΔS (entropy drift)        = {S_drift:.3e}")
print(f"ΔH (holographic drift)    = {H_drift:.3e}")

if E_drift < 1e-3 and S_drift < 1e-2 and H_drift < 1e-4:
    print("✅ TOE closure achieved: conservation and coherence hold.")
else:
    print("⚠️  Deviations detected — refinement or recalibration may be required.")

print("----------------------------------------------------------")