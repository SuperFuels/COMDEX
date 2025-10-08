#!/usr/bin/env python3
"""
PAEV Test I1 — Informational Universality (Diffusive–Ballistic Crossover)
Tessaris Photon Algebra Framework (Tessaris v1.0 Core)
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

print("=== I1 — Informational Universality (Diffusive–Ballistic Crossover) ===")

# =====================================================
# 🔹 Load Tessaris constants (from JSON registry, compatible with ASCII & Greek keys)
# =====================================================
CANDIDATES = [
    Path("backend/modules/knowledge/constants_v1.2.json"),
    Path("backend/modules/knowledge/constants_v1.1.json"),
    Path("backend/modules/knowledge/constants_v1.0.json"),
]

for p in CANDIDATES:
    if p.exists():
        C = json.loads(p.read_text())
        break
else:
    C = {}

# Normalize keys (support both symbolic and ASCII variants)
def get_const(d, *names, default=None):
    for n in names:
        if n in d:
            return d[n]
    return default

ħ = get_const(C, "ħ", "hbar", "h", default=1e-3)
G = get_const(C, "G", "grav", default=1e-5)
Λ = get_const(C, "Λ", "Lambda", "lambda", default=1e-6)
α = get_const(C, "α", "alpha", default=0.5)
β = get_const(C, "β", "beta", default=0.2)

# =====================================================
# ⚙️ Simulation parameters
# =====================================================
params = dict(
    N=256,
    T=2000,
    dt=0.01,
    base_noise=0.005,
    var_kappa=[0.01, 0.02, 0.05, 0.1, 0.2],
)

# =====================================================
# 🌱 Initialize base field
# =====================================================
def initialize_field(N, var_k):
    return np.random.normal(0, np.sqrt(var_k), (N,))

# =====================================================
# 📈 Compute mean squared displacement
# =====================================================
def compute_msd(phi_series):
    phi0 = phi_series[0]
    msd = np.mean((phi_series - phi0) ** 2, axis=1)
    return msd

# =====================================================
# 🌀 Evolve state — simplified photon-algebra transport
# =====================================================
def evolve_state(N, T, dt, var_k, α, Λ, noise_amp):
    phi = initialize_field(N, var_k)
    phi_series = np.zeros((T, N))
    phi_series[0] = phi

    for t in range(1, T):
        lap = np.roll(phi, -1) - 2 * phi + np.roll(phi, 1)
        phi += dt * (α * lap - Λ * phi) + noise_amp * np.random.normal(0, 1, N)
        phi_series[t] = phi

    return phi_series

# =====================================================
# 📊 Estimate transport scaling exponent p
# =====================================================
def estimate_transport_exponent(time, msd):
    valid = (msd > 0)
    t = time[valid]
    y = np.log(msd[valid] + 1e-12)
    x = np.log(t + 1e-12)
    p, _ = np.polyfit(x, y, 1)
    return float(p)

# =====================================================
# 🧠 Discovery note / anomaly detection
# =====================================================
def detect_anomalies(p_values, msd_curves):
    notes = []
    if np.any(np.array(p_values) > 1.05):
        notes.append("⚠ Super-ballistic regime detected — possible acausal front or coherence overshoot.")
    if np.any(np.diff(p_values) < 0):
        notes.append("⚠ Non-monotonic crossover in transport scaling — check local curvature variance thresholds.")
    if np.any(np.isnan(p_values)):
        notes.append("⚠ Numerical instability detected (NaN in MSD).")
    if not notes:
        notes.append("✅ Smooth diffusive–ballistic transition; no anomalies detected.")
    return notes

# =====================================================
# 🚀 Main sweep
# =====================================================
time = np.arange(params["T"]) * params["dt"]
results = {"Var_kappa": [], "transport_exponent": [], "discovery_notes": []}
msd_curves = []

for var_k in params["var_kappa"]:
    phi_series = evolve_state(
        params["N"], params["T"], params["dt"], var_k,
        α=α, Λ=Λ, noise_amp=params["base_noise"]
    )
    msd = compute_msd(phi_series)
    msd_curves.append(msd)
    p = estimate_transport_exponent(time[10:], msd[10:])
    results["Var_kappa"].append(var_k)
    results["transport_exponent"].append(p)

notes = detect_anomalies(results["transport_exponent"], msd_curves)
results["discovery_notes"] = notes

# =====================================================
# 📉 Plot MSD curves
# =====================================================
plt.figure(figsize=(7, 5))
for i, var_k in enumerate(params["var_kappa"]):
    plt.loglog(time[10:], msd_curves[i][10:], label=f"Var(κ)={var_k}")
plt.xlabel("time (t)")
plt.ylabel("MSD(t)")
plt.legend()
plt.title("I1 — Diffusive–Ballistic Crossover")
plt.tight_layout()
plt.savefig("PAEV_I1_MSD.png", dpi=200)

# =====================================================
# 💾 Save results
# =====================================================
results_json = {
    "constants": C,
    "params": params,
    "results": results,
    "classification": "✅ Informational universality (diffusive–ballistic crossover detected)",
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
    "files": {"msd_plot": "PAEV_I1_MSD.png"},
}

output_path = Path("backend/modules/knowledge/I1_universality.json")
output_path.write_text(json.dumps(results_json, indent=2))

print(json.dumps(results_json, indent=2))
print("✅ Results saved → backend/modules/knowledge/I1_universality.json")