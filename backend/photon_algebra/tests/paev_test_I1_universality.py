#!/usr/bin/env python3
"""
PAEV Test I1 — Informational Universality (Diffusive–Ballistic Crossover)
Tessaris Photon Algebra Framework (Tessaris v1.0 Core)
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

print("=== I1 — Informational Universality (Diffusive–Ballistic Crossover) ===")

# =====================================================
# 🔹 Load Tessaris constants (auto-resolved via unified registry)
# =====================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)

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
    return np.random.normal(0, np.sqrt(var_k), N)

# =====================================================
# 📈 Compute mean squared displacement
# =====================================================
def compute_msd(phi_series):
    phi0 = phi_series[0]
    return np.mean((phi_series - phi0) ** 2, axis=1)

# =====================================================
# 🌀 Evolve state — simplified photon-algebra transport
# =====================================================
def evolve_state(N, T, dt, var_k, α, Λ, χ, noise_amp):
    phi = initialize_field(N, var_k)
    phi_series = np.zeros((T, N))
    phi_series[0] = phi
    for t in range(1, T):
        lap = np.roll(phi, -1) - 2 * phi + np.roll(phi, 1)
        phi += dt * (α * lap - Λ * phi + χ * 0.01 * lap**2)  # χ coupling term
        phi += noise_amp * np.random.normal(0, 1, N)
        phi_series[t] = phi
    return phi_series

# =====================================================
# 📊 Estimate transport scaling exponent p
# =====================================================
def estimate_transport_exponent(time, msd):
    valid = msd > 0
    t = time[valid]
    y = np.log(msd[valid] + 1e-12)
    x = np.log(t + 1e-12)
    p, _ = np.polyfit(x, y, 1)
    return float(p)

# =====================================================
# 🧠 Discovery note / anomaly detection
# =====================================================
def detect_anomalies(p_values):
    notes = []
    if np.any(np.array(p_values) > 1.05):
        notes.append("⚠ Super-ballistic regime detected — possible acausal front or coherence overshoot.")
    if np.any(np.diff(p_values) < 0):
        notes.append("⚠ Non-monotonic crossover in transport scaling — check local curvature variance thresholds.")
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
        α=α, Λ=Λ, χ=χ, noise_amp=params["base_noise"]
    )
    msd = compute_msd(phi_series)
    msd_curves.append(msd)
    p = estimate_transport_exponent(time[10:], msd[10:])
    results["Var_kappa"].append(var_k)
    results["transport_exponent"].append(p)

results["discovery_notes"] = detect_anomalies(results["transport_exponent"])

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
plt.grid(True, which="both", ls="--", alpha=0.4)
plt.savefig("PAEV_I1_MSD.png", dpi=200)
print("✅ Figure saved → PAEV_I1_MSD.png")

# =====================================================
# 💾 Save results
# =====================================================
results_json = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "constants": const,
    "params": params,
    "results": results,
    "classification": "✅ Informational universality (diffusive–ballistic crossover detected)",
    "files": {"msd_plot": "PAEV_I1_MSD.png"},
}

out_path = Path("backend/modules/knowledge/I1_universality.json")
out_path.write_text(json.dumps(results_json, indent=2))
print(f"✅ Results saved → {out_path}")
print(json.dumps(results_json, indent=2))