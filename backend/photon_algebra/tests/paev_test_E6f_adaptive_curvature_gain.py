#!/usr/bin/env python3
"""
E6f — Adaptive Curvature Gain (β-weighted)
-----------------------------------------
Tests whether curvature feedback that scales with the entropy rate
achieves geometry-invariant universality across distinct IC types.

γ_κ(t) = γ_κ⁰ * (1 + β * |dS/dt|)
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# ==============================================================
# Configuration
# ==============================================================
IC_types = ["hot_shell", "cold_spike", "multi_blob"]
ħ, G, Λ, α, β_const = 1e-3, 1e-5, 1e-6, 0.5, 0.2
N, T, dt = 512, 3000, 0.01
base_noise = 0.008
gamma_S = 2.5
gamma_kappa0 = 1.0
beta_adapt = 4.0  # adaptive weighting coefficient

rng = np.random.default_rng(42)
t = np.arange(T) * dt

# ==============================================================
# Synthetic IC generators
# ==============================================================
def make_ic(kind):
    x = np.linspace(0, 2 * np.pi, N)
    if kind == "hot_shell":
        return np.exp(-0.5 * (x - np.pi) ** 2 / 0.3**2)
    elif kind == "cold_spike":
        return -np.exp(-0.5 * (x - np.pi/2) ** 2 / 0.2**2)
    elif kind == "multi_blob":
        return (np.sin(3*x) + 0.5*np.sin(7*x))
    else:
        raise ValueError(kind)

# ==============================================================
# Core evolution model (simplified symbolic stand-in)
# ==============================================================
def evolve_state(phi0):
    phi = phi0.copy()
    entropy = []
    curvature = []

    for i in range(T):
        noise = base_noise * rng.standard_normal(N)
        dphi = np.gradient(phi)
        lap = np.gradient(dphi)
        S = np.log1p(np.mean(phi**2) + 1e-9)
        entropy.append(S)

        # approximate curvature measure
        kappa = np.mean(np.abs(lap))
        curvature.append(kappa)

        # compute adaptive curvature gain
        if i > 0:
            dSdt = abs((entropy[-1] - entropy[-2]) / dt)
        else:
            dSdt = 0.0
        gamma_kappa_t = gamma_kappa0 * (1.0 + beta_adapt * dSdt)

        phi += dt * (-alpha * lap + Λ * phi - G * phi**3)
        phi += dt * gamma_S * (S - np.mean(entropy))
        phi -= dt * gamma_kappa_t * kappa * phi
        phi += noise

    phi_mean = np.mean(phi)
    curv_exp = np.mean(curvature)
    entropy_rate = np.mean(np.gradient(entropy))
    mean_curv = np.mean(curvature)

    return phi_mean, curv_exp, entropy_rate, mean_curv

# ==============================================================
# Run sweep
# ==============================================================
metrics = {"Phi_mean": [], "curv_exp": [], "entropy_rate": [], "mean_curv": []}

for kind in IC_types:
    phi0 = make_ic(kind)
    results = evolve_state(phi0)
    for key, val in zip(metrics.keys(), results):
        metrics[key].append(val)

# ==============================================================
# Collapse deviation
# ==============================================================
def rms_dev(a):
    a = np.array(a, dtype=float)
    return float(np.sqrt(np.nanmean((a - np.nanmean(a)) ** 2)))

collapse_dev = {k: rms_dev(metrics[k]) for k in metrics}

# ==============================================================
# Classification logic
# ==============================================================
if collapse_dev["mean_curv"] < 0.3 and collapse_dev["Phi_mean"] < 0.1:
    classification = "✅ Geometry invariant universality"
elif collapse_dev["curv_exp"] < 0.1 and collapse_dev["entropy_rate"] < 0.01:
    classification = "⚠️ Nearly invariant"
else:
    classification = "❌ Residual IC dependence"

# ==============================================================
# Visualization
# ==============================================================
plt.figure(figsize=(7, 4))
colors = ["tab:blue", "tab:orange", "tab:green"]
for k, c in zip(IC_types, colors):
    i = IC_types.index(k)
    plt.scatter(metrics["Phi_mean"][i], metrics["curv_exp"][i],
                s=180, color=c, label=k)
plt.xlabel("⟨Φ⟩ / normalized")
plt.ylabel("Curvature exponent")
plt.title("E6f — Adaptive Curvature Gain (β-weighted)")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_E6f_AdaptiveCurvature.png")

# ==============================================================
# Save and print results
# ==============================================================
results = {
    "IC_types": IC_types,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β_const},
    "params": {
        "N": N, "T": T, "dt": dt,
        "base_noise": base_noise,
        "gamma_S": gamma_S,
        "gamma_kappa0": gamma_kappa0,
        "beta_adapt": beta_adapt,
    },
    "metrics": metrics,
    "collapse_dev": collapse_dev,
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

print("=== E6f — Adaptive Curvature Gain (β-weighted) ===")
print(json.dumps(results, indent=2))
outf = Path("backend/modules/knowledge/E6f_adaptive_curvature_gain.json")
outf.parent.mkdir(parents=True, exist_ok=True)
outf.write_text(json.dumps(results, indent=2))
print(f"✅ Results saved → {outf}")