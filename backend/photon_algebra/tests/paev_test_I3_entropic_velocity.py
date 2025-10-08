#!/usr/bin/env python3
"""
PAEV Test I3 — Entropic Velocity & Causal Information Front
Tessaris Photon Algebra Framework
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

print("=== I3 — Entropic Velocity & Causal Information Front ===")

# =====================================================
# Load constants (v1.2 registry compatible)
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
# Simulation parameters
# =====================================================
params = dict(
    N=256,
    T=4000,
    dt=0.01,
    base_noise=0.015,
    var_kappa=[0.01, 0.02, 0.05, 0.1, 0.2],
)

# =====================================================
# Helpers
# =====================================================
def initialize_field(N, var_k):
    return np.random.normal(0, np.sqrt(var_k), (N,))

def evolve_state(N, T, dt, var_k, α, Λ, noise_amp):
    phi = initialize_field(N, var_k)
    phi_series = np.zeros((T, N))
    phi_series[0] = phi
    for t in range(1, T):
        lap = np.roll(phi, -1) - 2 * phi + np.roll(phi, 1)
        phi += dt * (α * lap - Λ * phi) + noise_amp * np.random.normal(0, 1, N)
        phi_series[t] = phi
    return phi_series

def compute_entropy(phi_series):
    ent = []
    for frame in phi_series:
        hist, _ = np.histogram(np.abs(frame), bins=64, density=True)
        hist = hist[hist > 0]
        if len(hist) == 0:
            ent.append(0.0)
            continue
        S = -np.sum(hist * np.log(hist + 1e-12))
        ent.append(S)
    return np.array(ent)

def compute_msd(phi_series):
    phi0 = phi_series[0]
    return np.mean((phi_series - phi0) ** 2, axis=1)

def compute_front_velocity(entropy, msd, dt):
    """Estimate entropic velocity v_S = (dS/dt) / (dMSD/dt)."""
    dS = np.gradient(entropy, dt)
    dM = np.gradient(msd, dt)
    with np.errstate(divide='ignore', invalid='ignore'):
        vS = np.where(np.abs(dM) > 1e-12, dS / (dM + 1e-12), 0)
    vS = np.clip(vS, 0, np.nanquantile(vS, 0.99))  # trim outliers
    return np.nanmean(vS), vS

# =====================================================
# Discovery note system
# =====================================================
def detect_anomalies(v_means, v_critical):
    notes = []
    ratios = np.array(v_means) / v_critical
    if np.any(ratios > 1.05):
        notes.append("⚠ Super-causal propagation detected — possible tunnelling or coherence breach.")
    elif np.all(ratios < 1.0):
        notes.append("✅ Sub-causal regime — information propagation respects causal limits.")
    else:
        notes.append("⚠ Mixed regime — near-causal transitions detected (ballistic edge).")
    return notes

# =====================================================
# Main sweep
# =====================================================
results = {"Var_kappa": [], "mean_velocity": [], "discovery_notes": []}
v_means = []
v_curves = []

v_critical = np.sqrt(α / (Λ + 1e-12))  # effective causal speed scale

for var_k in params["var_kappa"]:
    phi_series = evolve_state(params["N"], params["T"], params["dt"], var_k, α=α, Λ=Λ, noise_amp=params["base_noise"])
    msd = compute_msd(phi_series)
    entropy = compute_entropy(phi_series)
    v_mean, v_curve = compute_front_velocity(entropy, msd, params["dt"])
    v_means.append(v_mean)
    v_curves.append(v_curve)
    results["Var_kappa"].append(var_k)
    results["mean_velocity"].append(v_mean)

notes = detect_anomalies(v_means, v_critical)
results["discovery_notes"] = notes

# =====================================================
# Plot: Mean velocity vs Var(kappa)
# =====================================================
plt.figure(figsize=(7,5))
plt.plot(params["var_kappa"], v_means, 'o-', label="Mean entropic velocity v_S")
plt.axhline(v_critical, color='r', linestyle='--', label="Causal limit v_c")
plt.xlabel("Curvature variance Var(κ)")
plt.ylabel("Mean entropic velocity v_S")
plt.legend()
plt.title("I3 — Entropic Velocity & Causal Information Front")
plt.tight_layout()
plt.savefig("PAEV_I3_EntropyVelocity.png", dpi=200)

# =====================================================
# Save results
# =====================================================
results_json = {
    "constants": C,
    "params": params,
    "results": results,
    "classification": "✅ Entropic velocity and causal information front characterized",
    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%MZ"),
    "files": {"velocity_plot": "PAEV_I3_EntropyVelocity.png"},
}

output_path = Path("backend/modules/knowledge/I3_entropic_velocity.json")
output_path.write_text(json.dumps(results_json, indent=2))

print(json.dumps(results_json, indent=2))
print("✅ Results saved → backend/modules/knowledge/I3_entropic_velocity.json")