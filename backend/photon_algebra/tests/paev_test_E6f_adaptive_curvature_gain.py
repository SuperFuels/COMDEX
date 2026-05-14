#!/usr/bin/env python3
"""
E6g - Log-Adaptive Universality (tanh-bounded curvature feedback)
-----------------------------------------------------------------
Adaptive curvature feedback with bounded hyperbolic tangent control:
    γ_κ(t) = γ_κ0 * [1 + β * tanh(|dS/dt|)]
This prevents runaway gain spikes seen in E6f while retaining 
responsiveness to entropy-rate fluctuations.
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
hbar, G, Lambda, alpha, beta_const = 1e-3, 1e-5, 1e-6, 0.5, 0.2
N, T, dt = 512, 3000, 0.01
base_noise = 0.008
gamma_S = 2.5
gamma_kappa0 = 1.0
beta_adapt = 3.0  # slightly gentler modulation for smoother curves

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
        return -np.exp(-0.5 * (x - np.pi / 2) ** 2 / 0.2**2)
    elif kind == "multi_blob":
        return np.sin(3 * x) + 0.5 * np.sin(7 * x)
    else:
        raise ValueError(kind)

# ==============================================================
# Core evolution model
# ==============================================================
def evolve_state(phi0):
    phi = phi0.copy()
    entropy, curvature, gamma_trace = [], [], []

    for i in range(T):
        noise = base_noise * rng.standard_normal(N)
        dphi = np.gradient(phi)
        lap = np.gradient(dphi)
        S = np.log1p(np.mean(phi**2) + 1e-9)
        entropy.append(S)

        # curvature proxy
        kappa = np.mean(np.abs(lap))
        curvature.append(kappa)

        # adaptive tanh-bounded feedback
        if i > 0:
            dSdt = abs((entropy[-1] - entropy[-2]) / dt)
        else:
            dSdt = 0.0
        gamma_kappa_t = gamma_kappa0 * (1.0 + beta_adapt * np.tanh(dSdt))
        gamma_trace.append(gamma_kappa_t)

        # update dynamics
        phi += dt * (-alpha * lap + Lambda * phi - G * phi**3)
        phi += dt * gamma_S * (S - np.mean(entropy))
        phi -= dt * gamma_kappa_t * kappa * phi
        phi += noise

    phi_mean = np.mean(phi)
    curv_exp = np.mean(curvature)
    entropy_rate = np.mean(np.gradient(entropy))
    mean_curv = np.mean(curvature)
    return phi_mean, curv_exp, entropy_rate, mean_curv, gamma_trace

# ==============================================================
# Run across ICs
# ==============================================================
metrics = {"Phi_mean": [], "curv_exp": [], "entropy_rate": [], "mean_curv": []}
gamma_records = {}

for kind in IC_types:
    phi0 = make_ic(kind)
    phi_mean, curv_exp, entropy_rate, mean_curv, gamma_trace = evolve_state(phi0)
    metrics["Phi_mean"].append(phi_mean)
    metrics["curv_exp"].append(curv_exp)
    metrics["entropy_rate"].append(entropy_rate)
    metrics["mean_curv"].append(mean_curv)
    gamma_records[kind] = gamma_trace

# ==============================================================
# Collapse deviations
# ==============================================================
def rms_dev(a):
    a = np.array(a, dtype=float)
    return float(np.sqrt(np.nanmean((a - np.nanmean(a)) ** 2)))

collapse_dev = {k: rms_dev(metrics[k]) for k in metrics}

# ==============================================================
# Classification
# ==============================================================
if collapse_dev["mean_curv"] < 0.3 and collapse_dev["Phi_mean"] < 0.3:
    classification = "✅ Geometry invariant universality"
elif collapse_dev["curv_exp"] < 0.1 and collapse_dev["entropy_rate"] < 0.01:
    classification = "⚠️ Nearly invariant"
else:
    classification = "❌ IC-dependent"

# ==============================================================
# Visualization
# ==============================================================
colors = ["tab:blue", "tab:orange", "tab:green"]

# Universality plot
plt.figure(figsize=(7, 4))
for k, c in zip(IC_types, colors):
    i = IC_types.index(k)
    plt.scatter(metrics["Phi_mean"][i], metrics["curv_exp"][i], s=180, color=c, label=k)
plt.xlabel("⟨Φ⟩ (normalized)")
plt.ylabel("Curvature exponent")
plt.title("E6g - Log-Adaptive Universality (tanh-bounded γk)")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_E6g_LogAdaptive.png")

# Adaptive feedback traces
plt.figure(figsize=(8, 4))
for k, c in zip(IC_types, colors):
    plt.plot(t, gamma_records[k], label=f"{k} γk(t)", lw=1.2, color=c)
plt.xlabel("time")
plt.ylabel("γk(t)")
plt.title("Adaptive Curvature Feedback Evolution (tanh-bounded)")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_E6g_GammaTrace.png")

# ==============================================================
# Save + Print Results
# ==============================================================
results = {
    "IC_types": IC_types,
    "constants": {"ħ": hbar, "G": G, "Λ": Lambda, "α": alpha, "β": beta_const},
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
    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%MZ"),
    "files": {
        "universality_plot": "PAEV_E6g_LogAdaptive.png",
        "gamma_trace_plot": "PAEV_E6g_GammaTrace.png"
    },
}

print("=== E6g - Log-Adaptive Universality (tanh-bounded) ===")
print(json.dumps(results, indent=2))

outf = Path("backend/modules/knowledge/E6g_log_adaptive_universality.json")
outf.parent.mkdir(parents=True, exist_ok=True)
outf.write_text(json.dumps(results, indent=2))
print(f"✅ Results saved -> {outf}")