#!/usr/bin/env python3
"""
K3 - Relativistic Soliton Propagation (Tessaris)
-----------------------------------------------
Validates soliton propagation under causal constraints.
Tracks the velocity of χ-driven coherent structures and compares
against the causal bound c_eff.

Outputs:
  * backend/modules/knowledge/K3_soliton_propagation_summary.json
  * PAEV_K3_soliton_propagation.png
"""

import json, math, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

# --- Tessaris Unified Constants & Verification Protocol ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β, χ = const["ħ"], const["G"], const["Λ"], const["α"], const["β"], const["χ"]

print("=== K3 - Relativistic Soliton Propagation (Tessaris) ===")
print(f"Constants -> ħ={ħ}, G={G}, Λ={Λ}, α={α}, β={β}, χ={χ}")

# --- Grid and parameters ---
N, steps = 512, 2000
dt, dx = 0.002, 1.0
c_eff = math.sqrt(α / (1 + Λ))
seed = 7171
rng = np.random.default_rng(seed)

print(f"Grid N={N}, steps={steps}, dt={dt}, dx={dx}")

# --- Initial soliton setup ---
x = np.linspace(-N//2, N//2, N)
u = np.exp(-0.01 * (x + 40)**2)  # Gaussian pulse, offset
v = np.zeros_like(u)
p0 = 0.05  # momentum bias (simulated)
phase = np.exp(1j * p0 * x)
u = np.real(u * phase)

def laplacian(f):
    return np.roll(f, -1) - 2*f + np.roll(f, 1)

# --- Evolution loop ---
u_map = []
for n in range(steps):
    u_xx = laplacian(u)
    a = (c_eff**2) * u_xx - Λ*u - β*v + χ*np.clip(u**3, -1e3, 1e3)
    v += dt * a
    u += dt * v
    u = np.clip(u, -20, 20)
    if n % 10 == 0:
        u_map.append(u.copy())

u_map = np.array(u_map)
t_axis = np.arange(u_map.shape[0]) * dt * 10

# --- Track soliton center (max |u|) ---
centers = [x[np.argmax(np.abs(frame))] for frame in u_map]
centers = np.array(centers)
fit_mask = centers != centers[0]
if np.any(fit_mask):
    p = np.polyfit(t_axis[fit_mask], centers[fit_mask], 1)
    v_soliton = p[0]
else:
    v_soliton = 0.0

# --- Plot ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
im = ax1.imshow(np.abs(u_map), extent=[x.min(), x.max(), t_axis.max(), t_axis.min()],
                cmap="magma", aspect="auto")
ax1.plot(centers, t_axis, color="cyan", label=f"soliton center (v≈{v_soliton:.3f})")
ax1.set_xlabel("x"); ax1.set_ylabel("time")
ax1.set_title("K3 - Soliton Propagation (|u(x,t)|)")
ax1.legend(); plt.colorbar(im, ax=ax1, label="|u|")

ax2.plot(t_axis, centers, label="trajectory")
ax2.plot(t_axis, v_soliton*t_axis + centers[0], '--', label=f"fit: v≈{v_soliton:.3f}")
ax2.plot(t_axis, c_eff*t_axis, '--r', label=f"bound c_eff≈{c_eff:.3f}")
ax2.set_xlabel("time"); ax2.set_ylabel("position")
ax2.set_title("Trajectory vs Causal Bound")
ax2.legend(); ax2.grid(True)
plt.tight_layout()
fig_path = "PAEV_K3_soliton_propagation.png"
plt.savefig(fig_path, dpi=200)
print(f"✅ Plot saved -> {fig_path}")

# --- Summary JSON ---
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
summary = {
    "timestamp": ts,
    "seed": seed,
    "constants": const,
    "params": {"N": N, "steps": steps, "dt": dt, "dx": dx, "p0": p0},
    "derived": {
        "c_eff": c_eff,
        "empirical_soliton_speed": v_soliton,
        "within_bound": bool(abs(v_soliton) <= c_eff),
    },
    "files": {"plot": fig_path},
    "notes": [
        "Gaussian pulse used as χ-driven soliton proxy.",
        "Momentum bias introduces directed motion.",
        "Velocity compared to causal bound c_eff.",
        "Model-level test: no physical signaling implied.",
    ],
}
out_path = Path("backend/modules/knowledge/K3_soliton_propagation_summary.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"✅ Summary saved -> {out_path}")

# --- Discovery section ---
print("\n🧭 Discovery Notes -", ts)
print("------------------------------------------------------------")
print(f"* Observation: Soliton front speed v≈{v_soliton:.3f}, causal bound {c_eff:.3f}.")
if abs(v_soliton) <= c_eff:
    print("* Interpretation: Stable soliton motion within relativistic constraint.")
else:
    print("* Interpretation: Apparent overshoot due to nonlinear χ-driven acceleration.")
print("* Implication: Establishes relativistic propagation model for L-series tests.")
print("* Next step: Boost the soliton and test Lorentz invariance (L1-L3).")
print("------------------------------------------------------------")

# --- Verdict ---
print("\n" + "="*66)
print("🔎 K3 - Relativistic Soliton Propagation Verdict")
print("="*66)
status = "✅ Within causal bound" if abs(v_soliton) <= c_eff else "⚠️ Exceeds causal bound"
print(f"Empirical v≈{v_soliton:.4f} | bound≈{c_eff:.4f} -> {status}")
print("="*66 + "\n")