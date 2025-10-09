#!/usr/bin/env python3
"""
PAEV Test I4 — Entropy–Flux Synchronization (Information Lead / Tunnelling Detection)
Tessaris Photon Algebra Framework (Registry-aligned)
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path
from scipy.signal import correlate

print("=== I4 — Entropy–Flux Synchronization (Information Lead / Tunnelling Detection) ===")

# =====================================================
# 🔹 Load Tessaris constants from unified registry
# =====================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)  # new nonlinear coupling

# =====================================================
# ⚙️ Simulation parameters
# =====================================================
params = dict(
    N=256,
    T=4000,
    dt=0.01,
    base_noise=0.015,
    var_kappa=[0.01, 0.02, 0.05, 0.1, 0.2],
)

# =====================================================
# 🌱 Core field evolution
# =====================================================
def initialize_field(N, var_k):
    return np.random.normal(0, np.sqrt(var_k), N)

def evolve_state(N, T, dt, var_k, α, Λ, χ, noise_amp):
    """Evolve field under α–Λ–χ coupling (diffusive–entropic dynamics)."""
    phi = initialize_field(N, var_k)
    phi_series = np.zeros((T, N))
    phi_series[0] = phi
    for t in range(1, T):
        lap = np.roll(phi, -1) - 2 * phi + np.roll(phi, 1)
        # χ adds nonlinear phase coupling between entropy and curvature
        phi += dt * (α * lap - Λ * phi + χ * 0.01 * lap**2)
        phi += noise_amp * np.random.normal(0, 1, N)
        phi_series[t] = phi
    return phi_series

# =====================================================
# 📈 Compute entropy and flux
# =====================================================
def compute_entropy(phi_series):
    ent = []
    for frame in phi_series:
        hist, _ = np.histogram(np.abs(frame), bins=64, density=True)
        hist = hist[hist > 0]
        S = -np.sum(hist * np.log(hist + 1e-12)) if len(hist) else 0.0
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
# ⏱ Cross-correlation phase analysis
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
# 🧠 Discovery detection
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
# 🚀 Main experiment loop
# =====================================================
results = {"Var_kappa": [], "phase_lead_dt": [], "discovery_notes": []}
phase_leads = []

for var_k in params["var_kappa"]:
    phi_series = evolve_state(
        params["N"], params["T"], params["dt"],
        var_k, α=α, Λ=Λ, χ=χ, noise_amp=params["base_noise"]
    )
    entropy = compute_entropy(phi_series)
    flux = compute_flux(phi_series, α)
    Δt = compute_phase_lead(entropy, flux, params["dt"])
    phase_leads.append(Δt)
    results["Var_kappa"].append(var_k)
    results["phase_lead_dt"].append(Δt)

notes = detect_anomalies(phase_leads)
results["discovery_notes"] = notes

# =====================================================
# 📊 Plot results
# =====================================================
plt.figure(figsize=(7, 5))
plt.plot(params["var_kappa"], phase_leads, "o-", lw=1.5, label="Phase lead Δt")
plt.axhline(0, color="gray", linestyle="--", label="Synchronized boundary")
plt.xlabel("Curvature variance Var(κ)")
plt.ylabel("Phase lead Δt (entropy vs flux)")
plt.legend()
plt.title("I4 — Entropy–Flux Synchronization (Phase Analysis)")
plt.grid(True, which="both", ls="--", alpha=0.4)
plt.tight_layout()
plt.savefig("PAEV_I4_EntropyFluxSync.png", dpi=200)
print("✅ Figure saved → PAEV_I4_EntropyFluxSync.png")

# =====================================================
# 💾 Save results
# =====================================================
results_json = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "constants": const,
    "params": params,
    "results": results,
    "classification": "✅ Entropy–flux synchronization characterized",
    "files": {"sync_plot": "PAEV_I4_EntropyFluxSync.png"},
}

out_path = Path("backend/modules/knowledge/I4_entropy_flux_sync.json")
out_path.write_text(json.dumps(results_json, indent=2))
print(f"✅ Results saved → {out_path}")
print(json.dumps(results_json, indent=2))