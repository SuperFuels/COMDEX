# -*- coding: utf-8 -*-
"""
F13b - Dynamic Λ Feedback Evolution (DC-cancelled, stabilized)
--------------------------------------------------------------
Stabilizers (final):
  * dΛ/dt = γ_eff * Δn  - ζ (Λ - Λ_eq)  - ν * I
  * I'   = -ρ I + Δn_hp         (leaky integral of *high-passed* error)
  * DC cancel: ν = γ_base * ρ   (kills steady-state drift)
  * γ_eff = γ_base / (1 + κ |Δn|)  (adaptive gain)
  * Dead-band + softsat on Δn to suppress micro-chatter
  * Anti-windup clamp on I

Outputs:
  * PAEV_F13b_LambdaEvolution.png
  * PAEV_F13b_SEEvolution.png
  * PAEV_F13b_PhaseFeedback.png
  * backend/modules/knowledge/F13b_dynamic_vacuum_feedback.json
"""
from pathlib import Path
from datetime import datetime, timezone
import json, numpy as np, matplotlib.pyplot as plt

# ---------- constants (fallback chain)
CANDIDATES = [
    Path("backend/modules/knowledge/constants_v1.2.json"),
    Path("backend/modules/knowledge/constants_v1.1.json"),
    Path("backend/modules/knowledge/constants_v1.0.json"),
]
for p in CANDIDATES:
    if p.exists():
        constants = json.loads(p.read_text()); break
else:
    constants = {}
ħ = float(constants.get("ħ", 1e-3))
G = float(constants.get("G", 1e-5))
α = float(constants.get("α", 0.5))
Λ0 = float(constants.get("Λ", 1e-6))

# ---------- drivers (abstract proxies)
T, dt = 2400, 0.006
t = np.arange(T) * dt
# Curvature-energy & entropy proxies (mildly nonstationary but bounded)
E = 0.10*np.sin(0.6 + 0.45*t) + 0.05*np.cos(0.23*t)
S = 0.70 + 0.05*np.sin(0.18*t + 0.7)

def ema(prev, x, a=0.03): return (1-a)*prev + a*x if prev is not None else x
E_sm_prev = S_sm_prev = None

# ---------- Λ dynamics (anti-drift with DC cancel)
Λ = np.zeros_like(t); Λ[0] = Λ0; Λ_eq = Λ0

# Final zero-drift gains (stable, tight)
γ_base  = 0.0022     # slightly gentler P gain
ζ       = 1.45       # stronger pull to Λ_eq
κ_adapt = 11.0       # adaptive softening
ρ       = 0.080      # integral leak
ν       = 1.15 * γ_base * ρ   # 15% over-cancel to kill bias

# Error processing (bias removal + chatter suppression)
deadband = 3.0e-3    # ignore tiny errors
softsat_k = 9.5      # tanh soft saturation
hp_ema    = 0.040    # faster DC tracker for high-pass
I_clamp   = 0.040    # anti-windup bound on |I|

I_int = 0.0
Δn_mean = 0.0  # running mean for high-pass
dS_hist, dE_hist = [], []

# Normalization scale for error (keeps Δn O(1))
S_mu, E_mu = np.mean(S), np.mean(E)
σ_S, σ_E = np.std(S - S_mu), np.std(E - E_mu)
σ_sum = σ_S + σ_E + 1e-9

for k in range(1, T):
    # Smooth drivers
    E_sm = ema(E_sm_prev, E[k]); E_sm_prev = E_sm
    S_sm = ema(S_sm_prev, S[k]); S_sm_prev = S_sm
    dE = E_sm - E[k-1]; dS = S_sm - S[k-1]
    dE_hist.append(dE); dS_hist.append(dS)

    # Normalized error with dead-band + soft saturation
    raw = (dS - dE) / σ_sum
    if abs(raw) < deadband:
        raw = 0.0
    Δn_sat = np.tanh(softsat_k * raw) / softsat_k

    # High-pass the error (remove DC bias)
    Δn_mean = (1 - hp_ema) * Δn_mean + hp_ema * Δn_sat
    Δn_hp   = Δn_sat - Δn_mean

    # Adaptive proportional gain (use HP error too)
    γ_eff = γ_base / (1.0 + κ_adapt * abs(Δn_hp))

    # Leaky integral on HP error (with anti-windup)
    I_int += dt * (-ρ * I_int + Δn_hp)
    I_int = np.clip(I_int, -I_clamp, I_clamp)

    # Λ update: **P and I both use HP error**
    dΛ = γ_eff * Δn_hp - ζ * (Λ[k-1] - Λ_eq) - ν * I_int
    Λ[k] = Λ[k-1] + dt * dΛ

# ---------- diagnostics
tail_n = max(200, T // 8)
Λ_drift = float(Λ[-1] - Λ_eq)
Λ_tail_std = float(np.std(Λ[-tail_n:]))
stable = (abs(Λ_drift) < 5e-6) and (Λ_tail_std < 8e-5)
classification = "✅ Λ self-stabilized (attractor reached)" if stable else "⚠️ Λ drift detected (requires tuning)"

print("=== F13b - Dynamic Λ Feedback Evolution Test (DC-cancelled) ===")
print(f"ħ={ħ:.1e}, α={α:.2f}, Λ0={Λ0:.2e}, γ={γ_base:.4f}, ζ={ζ:.2f}, κ={κ_adapt:.1f}, ρ={ρ:.3f}, ν={ν:.6f}")
print(f"Λ_final={Λ[-1]:.6f} | drift={Λ_drift:.6f} | tail σ={Λ_tail_std:.6f}")
print(f"-> {classification}")

# ---------- plots
out = Path(".")
plt.figure(figsize=(11,4))
plt.plot(t, Λ, lw=1.8, label="Λ(t)")
plt.axhline(Λ0, ls="--", c="gray", lw=1, label="Λ0")
plt.title("F13b - Dynamic Vacuum Feedback Evolution (stabilized)")
plt.xlabel("time"); plt.ylabel("Λ(t)"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_F13b_LambdaEvolution.png", dpi=160)

plt.figure(figsize=(11,4))
plt.plot(t, S, label="Entropy S(t)", lw=1.6)
plt.plot(t, E, label="Curvature Energy E(t)", lw=1.6)
plt.title("F13b - Entropy and Curvature Energy Evolution")
plt.xlabel("time"); plt.ylabel("Magnitude"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_F13b_SEEvolution.png", dpi=160)

ΔS = np.array(dS_hist); ΔE = np.array(dE_hist)
σ = (σ_sum + 1e-12)
plt.figure(figsize=(6.4,6))
plt.plot(ΔS/σ, (ΔS-ΔE)/σ, lw=1.6)
plt.title("F13b - Feedback Phase Space (ΔS vs ΔΛ)")
plt.xlabel("ΔS (normalized)"); plt.ylabel("ΔΛ (normalized)")
plt.tight_layout(); plt.savefig(out/"PAEV_F13b_PhaseFeedback.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_F13b_LambdaEvolution.png")
print("  - PAEV_F13b_SEEvolution.png")
print("  - PAEV_F13b_PhaseFeedback.png")

# ---------- knowledge card
summary = {
    "ħ": ħ, "G": G, "α": α,
    "Λ0": Λ0, "γ": γ_base, "ζ": ζ, "κ": κ_adapt, "ν": ν, "ρ": ρ,
    "timing": {"steps": T, "dt": dt},
    "metrics": {
        "Λ_final": float(Λ[-1]),
        "Λ_drift": Λ_drift,
        "Λ_tail_std": Λ_tail_std,
        "S_mean": float(np.mean(S)),
        "E_mean": float(np.mean(E)),
    },
    "classification": classification,
    "files": {
        "lambda_plot": "PAEV_F13b_LambdaEvolution.png",
        "entropy_energy_plot": "PAEV_F13b_SEEvolution.png",
        "phase_feedback_plot": "PAEV_F13b_PhaseFeedback.png",
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
Path("backend/modules/knowledge/F13b_dynamic_vacuum_feedback.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved -> backend/modules/knowledge/F13b_dynamic_vacuum_feedback.json")