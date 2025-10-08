#!/usr/bin/env python3
"""
PAEV Test I4 — Entropy–Flux Synchronization (Information Lead / Tunnelling Detection)
Tessaris Photon Algebra Framework
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from scipy.signal import correlate

print("=== I4 — Entropy–Flux Synchronization (Information Lead / Tunnelling Detection) ===")

# =====================================================
# Load constants (compatible with v1.2 registry)
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
# Parameters
# =====================================================
params = dict(
    N=256,
    T=4000,
    dt=0.01,
    base_noise=0.015,
    var_kappa=[0.01, 0.02, 0.05, 0.1, 0.2],
)

# =====================================================
# Core field evolution
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

# =====================================================
# Compute entropy and energy flux
# =====================================================
def compute_entropy(phi_series):
    ent = []
    for frame in phi_series:
        hist, _ = np.histogram(np.abs(frame), bins=64, density=True)
        hist = hist[hist > 0]
        S = -np.sum(hist * np.log(hist))
        ent.append(S)
    return np.array(ent)

def compute_flux(phi_series, α):
    """Approximate local energy flux from Laplacian energy term."""
    flux = []
    for frame in phi_series:
        lap = np.roll(frame, -1) - 2 * frame + np.roll(frame, 1)
        F = np.mean(np.abs(α * lap * frame))
        flux.append(F)
    return np.array(flux)

# =====================================================
# Cross-correlation phase analysis
# =====================================================
def compute_phase_lead(entropy, flux, dt):
    """Return lead/lag time Δt between entropy rate and flux."""
    dS = np.gradient(entropy)
    dF = np.gradient(flux)
    corr = correlate(dS - np.mean(dS), dF - np.mean(dF), mode="full")
    lags = np.arange(-len(dS) + 1, len(dS))
    lag_idx = np.argmax(corr)
    lag_time = lags[lag_idx] * dt
    return lag_time

# =====================================================
# Discovery detection
# =====================================================
def detect_anomalies(phase_leads):
    notes = []
    leads = np.array(phase_leads)
    if np.any(leads < 0):
        notes.append("⚠ Information-first regime detected (Δt < 0) — tunnelling-like behavior.")
    if np.any(leads > 0.05):
        notes.append("⚠ Energy-lag regime detected — delayed entropy response.")
    if not notes:
        notes.append("✅ Entropy and flux remain synchronized within resolution.")
    return notes

# =====================================================
# Main experiment loop
# =====================================================
results = {"Var_kappa": [], "phase_lead_dt": [], "discovery_notes": []}
phase_leads = []

for var_k in params["var_kappa"]:
    phi_series = evolve_state(params["N"], params["T"], params["dt"], var_k, α=α, Λ=Λ, noise_amp=params["base_noise"])
    entropy = compute_entropy(phi_series)
    flux = compute_flux(phi_series, α)
    Δt = compute_phase_lead(entropy, flux, params["dt"])
    phase_leads.append(Δt)
    results["Var_kappa"].append(var_k)
    results["phase_lead_dt"].append(Δt)

notes = detect_anomalies(phase_leads)
results["discovery_notes"] = notes

# =====================================================
# Plotting
# =====================================================
plt.figure(figsize=(7,5))
plt.plot(params["var_kappa"], phase_leads, "o-", lw=1.5)
plt.axhline(0, color="gray", linestyle="--")
plt.xlabel("Curvature variance Var(κ)")
plt.ylabel("Phase lead Δt (entropy vs flux)")
plt.title("I4 — Entropy–Flux Synchronization (Phase Analysis)")
plt.tight_layout()
plt.savefig("PAEV_I4_EntropyFluxSync.png", dpi=200)

# =====================================================
# Save results
# =====================================================
results_json = {
    "constants": C,
    "params": params,
    "results": results,
    "classification": "✅ Entropy–flux synchronization characterized",
    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%MZ"),
    "files": {"sync_plot": "PAEV_I4_EntropyFluxSync.png"},
}

out_path = Path("backend/modules/knowledge/I4_entropy_flux_sync.json")
out_path.write_text(json.dumps(results_json, indent=2))

print(json.dumps(results_json, indent=2))
print("✅ Results saved → backend/modules/knowledge/I4_entropy_flux_sync.json")