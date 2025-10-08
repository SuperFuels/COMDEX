# -*- coding: utf-8 -*-
"""
H3 — Information Topology Test (Registry-Compliant Dual-Mode Edition)
---------------------------------------------------------------------
Goal:
  Measure curvature of the information manifold via gradients in entropy density.
  At equilibrium, R_I → 0 indicates a flat (stable) information geometry.

Modes:
  • classical — baseline (no entanglement correlations)
  • entangled — introduces cross-field coherence and mutual-information modulation

Outputs:
  • H3_InformationTopology_classical.png
  • H3_InformationTopology_entangled.png
  • backend/modules/knowledge/H3_information_topology.json
"""

from pathlib import Path
from datetime import datetime, timezone
import numpy as np, json, matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# 1) Constants — Tessaris unified registry loader
# ---------------------------------------------------------------------
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ0, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# ---------------------------------------------------------------------
# 2) Simulation parameters
# ---------------------------------------------------------------------
T, dt = 2400, 0.006
x = np.linspace(-3, 3, 400)
t = np.arange(T) * dt

results = {}

# ---------------------------------------------------------------------
# 3) Run both topology modes
# ---------------------------------------------------------------------
for mode in ["classical", "entangled"]:
    # --- synthetic entropy field
    if mode == "classical":
        S_xt = np.array([
            0.70 + 0.05 * np.sin(0.2 * t_i + x) + 0.01 * np.cos(0.8 * x * t_i)
            for t_i in t
        ])
    else:  # entangled mode adds mutual-information modulation
        phase_coupling = 0.3 * np.sin(0.5 * t[:, None] - 0.8 * x[None, :])
        S_xt = np.array([
            0.70
            + 0.05 * np.sin(0.2 * t_i + x + phase_coupling[k])
            + 0.02 * np.cos(0.6 * x * t_i + 0.5 * phase_coupling[k])
            for k, t_i in enumerate(t)
        ])

    # --- compute curvature proxy
    Sx = np.gradient(S_xt, axis=1)
    Sxx = np.gradient(Sx, axis=1)
    R_I = np.mean(np.abs(Sxx / (S_xt + 1e-6)), axis=1)

    # --- equilibrium metrics
    R_I_eq = np.mean(R_I[-300:])
    flat = R_I_eq < 1e-3
    classification = (
        f"✅ Flat information manifold ({mode})"
        if flat
        else f"⚠️ Residual information curvature ({mode})"
    )

    # --- plot
    plt.figure(figsize=(10, 4))
    plt.plot(t, R_I, label=f"R_I(t) — {mode}", lw=1.5)
    plt.axhline(R_I_eq, ls="--", c="gray", lw=1)
    plt.title(f"H3 — Information Curvature Evolution ({mode} mode)")
    plt.xlabel("Time")
    plt.ylabel("R_I")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    fname = f"H3_InformationTopology_{mode}.png"
    plt.savefig(fname, dpi=150)
    plt.close()

    print(f"=== H3 — Information Topology Test ({mode}) ===")
    print(f"ħ={ħ:.1e}, G={G:.1e}, α={α:.2f}, Λ0={Λ0:.1e}, β={β:.2f}")
    print(f"R_I_eq={R_I_eq:.6e}")
    print(f"→ {classification}")
    print(f"✅ Plot saved: {fname}")

    # --- store mode results
    results[mode] = {
        "R_I_mean": float(np.mean(R_I)),
        "R_I_eq": float(R_I_eq),
        "classification": classification,
        "plot": fname,
    }

# ---------------------------------------------------------------------
# 4) Knowledge summary export
# ---------------------------------------------------------------------
summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α": α,
    "β": β,
    "modes": results,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
out_path = Path("backend/modules/knowledge/H3_information_topology.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved → {out_path}")