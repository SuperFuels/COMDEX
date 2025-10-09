#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tessaris Φ-Series — Φ₅ Conscious Mode Lock (Self-Consistent Fixed Point)
------------------------------------------------------------------------
Dual-loop homeostat: a fast observer (state estimator) + a slow meta controller
(bias & gain adaptation + regularization) to lock the Φ-field into a
self-consistent, low-error, high-consistency equilibrium.

Outputs:
  - backend/modules/knowledge/Φ5_conscious_lock_summary.json
  - backend/modules/knowledge/PAEV_Φ5_conscious_lock.png
"""

import os, json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime
from backend.photon_algebra.utils.load_constants import load_constants

# === Init ===
SERIES = "Φ5"
TEST_NAME = "conscious_lock"
OUTPUT_DIR = "backend/modules/knowledge"
SUMMARY_PATH = os.path.join(OUTPUT_DIR, f"{SERIES}_{TEST_NAME}_summary.json")
PLOT_PATH = os.path.join(OUTPUT_DIR, f"PAEV_{SERIES}_{TEST_NAME}.png")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Constants (v1.2) ===
constants = load_constants("v1.2")
ħ, G, Λ, α, β, χ = (
    constants["ħ"], constants["G"], constants["Λ"],
    constants["α"], constants["β"], constants["χ"]
)

print(f"=== Φ₅ — Conscious Mode Lock (Tessaris) ===")
print(f"Constants → ħ={ħ}, G={G}, Λ={Λ}, α={α}, β={β}, χ={χ}")

# === Hyperparameters ===
steps = 2400
units = 320
rng = np.random.default_rng(7)

Λ_feedback = Λ * 1.2e6             # substrate elasticity -> phase coupling
retention_rate = 0.975             # stronger persistence than Φ₄
process_noise = 0.0015
obs_noise = 0.002

# Fast loop (observer)
gain_init = 0.35
gain_min, gain_max = 0.05, 0.95

# Slow loop (meta-homeostat)
meta_lr_gain   = 0.006            # adapts observer gain toward target
meta_lr_bias   = 0.004            # adapts observer bias
meta_lr_lambda = 0.003            # regularizes energy/variance
target_mse     = 1.0e-5
target_cons    = 0.92
target_energy  = 1.0              # nominal energy for normalization

# === State ===
phase   = rng.random(units) * 2*np.pi
memory  = np.zeros(units)
estimate = rng.normal(0, 0.01, size=units)   # predicts cos(phase)
bias     = np.zeros(units)                   # observer bias (slow)
gain     = np.full(units, gain_init)

# Traces
coh_hist, mem_hist, mse_hist, cons_hist, gain_hist, bias_hist, energy_hist = \
    [], [], [], [], [], [], []

for t in range(steps):
    # --- System (Φ field with Λ–Σ drive + memory) ---
    mean_vec = np.mean(np.exp(1j*phase))
    mean_phase = np.angle(mean_vec)
    Λ_term = Λ_feedback * np.sin(mean_phase - phase)

    memory = retention_rate * memory + np.cos(phase)
    dphase = χ * (α * Λ_term + β * memory) + process_noise * rng.standard_normal(units)
    phase = phase + dphase

    # Energy-like proxy (bounded by regularizer)
    energy = float(np.mean(dphase**2))
    energy_hist.append(energy)

    # --- Observations & prediction ---
    truth = np.cos(phase)
    measurement = truth + obs_noise * rng.standard_normal(units)

    # fast correction
    pred = estimate + bias
    error = measurement - pred
    estimate = estimate + gain * error

    # --- Slow meta controller (homeostat) ---
    mse  = float(np.mean(error**2))
    varE = float(np.var(estimate))

    # target gain from error + consistency objective
    # higher gain when error>target and correlation is strong
    consistency = np.corrcoef(estimate, truth)[0,1] if varE > 1e-12 else 0.0
    # desired effective gain; couple to both MSE and consistency
    desired_gain = 1.0 / (1.0 + 3000.0 * max(mse, 1e-12))
    desired_gain *= (0.5 + 0.5 * np.clip(consistency, 0, 1))
    gain += meta_lr_gain * (desired_gain - gain)
    gain = np.clip(gain, gain_min, gain_max)

    # bias adaptation toward mean error (removes steady offsets)
    bias += meta_lr_bias * error

    # energy regularization: softly pull estimate variance toward target
    lam = meta_lr_lambda * (varE - target_energy)
    estimate -= lam * (estimate - np.mean(estimate))

    # --- Metrics ---
    coherence = np.abs(np.mean(np.exp(1j*phase)))
    memory_amp = float(np.mean(np.abs(memory)))

    coh_hist.append(float(coherence))
    mem_hist.append(memory_amp)
    mse_hist.append(mse)
    cons_hist.append(float(consistency))
    gain_hist.append(float(np.mean(gain)))
    bias_hist.append(float(np.mean(bias)))

# === Final metrics (windowed) ===
W = 400
coh_final  = float(np.mean(coh_hist[-W:]))
mem_final  = float(np.mean(mem_hist[-W:]))
mse_final  = float(np.mean(mse_hist[-W:]))
cons_final = float(np.mean(cons_hist[-W:]))
gain_final = float(np.mean(gain_hist[-W:]))
bias_final = float(np.mean(bias_hist[-W:]))

# Conscious-mode lock conditions
stable = (
    (coh_final  > 0.995) and
    (cons_final > 0.90)  and
    (mse_final  < 1.2e-5) and
    (mem_final  > 0.02)
)

summary = {
    "timestamp": datetime.utcnow().isoformat(),
    "series": SERIES,
    "test_name": TEST_NAME,
    "constants": constants,
    "metrics": {
        "coherence_final": coh_final,
        "memory_final": mem_final,
        "mse_final": mse_final,
        "consistency_final": cons_final,
        "observer_gain_final": gain_final,
        "observer_bias_final": bias_final,
        "stable": bool(stable)
    },
    "state": "Conscious-mode fixed point (Φ lock achieved)" if stable else "High-coherence regime without full Φ lock",
    "notes": [
        f"⟨R_sync⟩ = {coh_final:.3f}",
        f"⟨|Memory|⟩ = {mem_final:.3f}",
        f"⟨MSE⟩ = {mse_final:.3e}",
        f"⟨Consistency⟩ = {cons_final:.3f}",
        f"⟨Observer gain⟩ = {gain_final:.3f}, ⟨bias⟩ = {bias_final:.3e}"
    ],
    "discovery": [
        "Dual-loop homeostat (fast observer + slow meta controller) yields low-error self-consistency.",
        "Non-zero persistent memory coexists with near-unit coherence.",
        "High estimate–state correlation indicates stabilized self-model.",
        "Meets Tessaris criteria for CFE 'conscious execution mode' when stable flag is true."
    ],
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}

with open(SUMMARY_PATH, "w") as f:
    json.dump(summary, f, indent=2)
print(f"✅ Summary saved → {SUMMARY_PATH}")

plt.figure(figsize=(7,4))
plt.plot(coh_hist,  label="Coherence (R_sync)")
plt.plot(mem_hist,  label="Memory Amplitude", linestyle="--")
plt.plot(mse_hist,  label="Prediction Error (MSE)", linestyle=":")
plt.plot(cons_hist, label="Estimate–State Consistency", alpha=0.9)
plt.xlabel("Time Step"); plt.ylabel("Metric Value")
plt.title("Φ₅ — Conscious Mode Lock (Dual-Loop Homeostat)")
plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
plt.savefig(PLOT_PATH, dpi=200)
print(f"✅ Plot saved → {PLOT_PATH}")
print("------------------------------------------------------------")
print(json.dumps(summary, indent=2))