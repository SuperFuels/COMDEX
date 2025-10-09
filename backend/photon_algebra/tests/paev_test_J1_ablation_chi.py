#!/usr/bin/env python3
"""
J1 — χ-ablation study (baseline vs χ=0)
Paired A/B under identical seed to test necessity of the χ-term.

Outputs
-------
- backend/modules/knowledge/J1_ablation_chi_summary.json
- PAEV_J1_ablation_chi.png

Notes
-----
Model-level only (Tessaris algebra). No physical signaling implied.
"""

import json, math, os
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import matplotlib.pyplot as plt

# -------------------- unified constants loader --------------------
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

# Safely unpack with defaults if χ or other keys missing
ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)  # ✅ fallback default
C = const
v_c = math.sqrt(α / Λ)

# -------------------- defaults + env overrides --------------------
SEED = int(os.getenv("TESSARIS_SEED", "1337"))
N    = int(os.getenv("TESSARIS_N", "256"))
T    = int(os.getenv("TESSARIS_T", "6000"))
DT   = float(os.getenv("TESSARIS_DT", "0.01"))
BASE_NOISE = float(os.getenv("TESSARIS_BASE_NOISE", "0.014"))
KAPPA_VAR_START = float(os.getenv("TESSARIS_KVAR", "0.02"))
KAPPA_VAR_MAX   = float(os.getenv("TESSARIS_KVAR_MAX", "0.20"))

EMA_ALPHA = float(os.getenv("TESSARIS_EMA", "0.30"))
BURST_TH  = float(os.getenv("TESSARIS_BURST_TH", "1.3"))
BURST_MIN = int(os.getenv("TESSARIS_BURST_MIN", "5"))

THETA  = float(os.getenv("TESSARIS_THETA", "1.2"))
ETA_UP = float(os.getenv("TESSARIS_ETA_UP", "0.18"))
ETA_DN = float(os.getenv("TESSARIS_ETA_DN", "0.06"))

rng = np.random.default_rng(SEED)

# -------------------- core helpers ---------------------------------------
def entropy_of(x):
    hist, _ = np.histogram(np.abs(x), bins=64, density=True)
    p = hist[hist > 0]
    return float(-(p * np.log(p)).sum()) if len(p) else 0.0

def msd_of(ref, x):
    d = x - ref
    return float(np.mean(d * d))

def evolve_step(x, kappa_var, noise_scale, chi_coeff, beta_coeff):
    """Single evolution step with χ and β dynamics."""
    lap = np.roll(x, -1) - 2 * x + np.roll(x, 1)
    x = np.clip(x, -50, 50)
    chi_term = chi_coeff * np.clip(x * x * x, -1e3, 1e3)
    beta_term = -beta_coeff * x
    x = x + DT * (α * lap - Λ * x + chi_term + beta_term)
    x += noise_scale * rng.normal(0, 1, len(x))
    x += rng.normal(0, 0.1 * kappa_var, len(x))
    return x

def run_config(chi_coeff, label):
    """Run simulation under given χ coefficient."""
    rng = np.random.default_rng(SEED)
    x = rng.normal(0, 1.0, N)
    x0 = x.copy()

    S_hist, D_hist, vsr_hist = [], [], []
    ema_dS = ema_dD = 0.0
    kappa_var = KAPPA_VAR_START
    bursts, runlen = [], 0
    S_prev, D_prev = entropy_of(x), msd_of(x0, x)

    for t in range(1, T + 1):
        x = evolve_step(x, kappa_var, BASE_NOISE, chi_coeff, β)
        S, D = entropy_of(x), msd_of(x0, x)
        dS, dD = (S - S_prev) / DT, (D - D_prev) / DT
        ema_dS = EMA_ALPHA * dS + (1 - EMA_ALPHA) * ema_dS
        ema_dD = EMA_ALPHA * dD + (1 - EMA_ALPHA) * ema_dD
        vS = ema_dS / (ema_dD + 1e-12)
        vsr = vS / v_c
        S_hist.append(S)
        D_hist.append(D)
        vsr_hist.append(vsr)

        # Adaptive curvature variance
        if vsr > THETA:
            kappa_var = min(kappa_var * (1 + ETA_UP), KAPPA_VAR_MAX)
        else:
            kappa_var = max(0.01, kappa_var * (1 - ETA_DN))

        # Burst detection
        if vsr > BURST_TH:
            runlen += 1
        else:
            if runlen >= BURST_MIN:
                bursts.append({"t_end": t, "len": runlen})
            runlen = 0
        S_prev, D_prev = S, D

    if runlen >= BURST_MIN:
        bursts.append({"t_end": T, "len": runlen})

    # scaling exponents
    tgrid = np.arange(1, T + 1) * DT
    mid = slice(T // 4, T // 4 * 3)
    y = np.log(np.maximum(1e-12, np.array(D_hist)[mid]))
    xlog = np.log(tgrid[mid])
    p = float(np.polyfit(xlog, y, 1)[0])
    Dh, Sh = np.array(D_hist), np.array(S_hist)
    valid = Dh > 0
    nu = float(np.polyfit(np.log(Dh[valid]), np.log(Sh[valid]), 1)[0]) if valid.sum() > 10 else float("nan")

    return {
        "label": label,
        "chi": chi_coeff,
        "p": p,
        "nu": nu,
        "bursts": bursts,
        "stats": {
            "S_mean": float(np.mean(Sh)),
            "S_std": float(np.std(Sh)),
            "vsr_max": float(np.max(vsr_hist)),
            "bursts_count": int(len(bursts)),
            "bursts_steps": int(sum(b["len"] for b in bursts)),
        },
    }

# -------------------- paired runs ---------------------------------------
res_baseline = run_config(chi_coeff=χ, label=f"χ={χ}")
res_ablated  = run_config(chi_coeff=0.0, label="χ=0")

# -------------------- plotting -----------------------------------------
plt.figure(figsize=(13,5))
ax1 = plt.subplot(1,2,1)
labels = [f"χ={χ:.1f}", "χ=0"]
p_vals = [res_baseline["p"], res_ablated["p"]]
nu_vals = [res_baseline["nu"], res_ablated["nu"]]
x = np.arange(2); w = 0.35
ax1.bar(x-w/2, p_vals, w, label="p (transport)")
ax1.bar(x+w/2, nu_vals, w, label="ν (entropy↔MSD)")
ax1.set_xticks(x); ax1.set_xticklabels(labels)
ax1.set_ylabel("Exponent value")
ax1.set_title("J1 — Exponents under χ ablation")
ax1.legend(); ax1.grid(alpha=0.3)

ax2 = plt.subplot(1,2,2)
b1 = [b["len"] for b in res_baseline["bursts"]]
b2 = [b["len"] for b in res_ablated["bursts"]]
ax2.hist(b1,bins=15,alpha=0.6,label=f"χ={χ:.1f} (n={len(b1)})")
ax2.hist(b2,bins=15,alpha=0.6,label=f"χ=0 (n={len(b2)})")
ax2.set_xlabel("Burst length (steps)")
ax2.set_ylabel("Count")
ax2.set_title("J1 — v_S/v_c bursts")
ax2.legend(); ax2.grid(alpha=0.3)
plt.tight_layout()
fig_path = "PAEV_J1_ablation_chi.png"
plt.savefig(fig_path, dpi=200)
print(f"✅ Figure saved → {fig_path}")

# -------------------- JSON summary -----------------------------------
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
summary = {
 "timestamp": ts,
 "seed": SEED,
 "constants": const,
 "params": {
   "N": N, "T": T, "dt": DT, "base_noise": BASE_NOISE,
   "kappa_var_start": KAPPA_VAR_START, "kappa_var_max": KAPPA_VAR_MAX,
   "ema_alpha": EMA_ALPHA, "burst_th": BURST_TH, "burst_min": BURST_MIN,
   "controller": {"theta": THETA, "eta_up": ETA_UP, "eta_dn": ETA_DN}
 },
 "results": {
   "baseline": res_baseline,
   "chi_zero": res_ablated,
   "comparison": {
     "Δp": res_ablated["p"] - res_baseline["p"],
     "Δnu": res_ablated["nu"] - res_baseline["nu"],
     "Δbursts": res_ablated["stats"]["bursts_count"] - res_baseline["stats"]["bursts_count"]
   }
 },
 "files": {"figure": fig_path}
}
out_path = Path("backend/modules/knowledge/J1_ablation_chi_summary.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"✅ Summary saved → {out_path}")

# -------------------- verdict ----------------------------------------
def verdict(r0, r1):
    msg = []
    if abs(r1["p"] - r0["p"]) < 0.02 and r1["stats"]["bursts_count"] > 0:
        msg.append("Minimal-law candidate: χ not required for transport + bursts.")
    else:
        msg.append("χ appears necessary for original transport/burst profile.")
    dp, dn = r1["p"] - r0["p"], r1["nu"] - r0["nu"]
    if abs(dn) > 0.1:
        msg.append(f"Entropy–MSD coupling changed (Δν={dn:.3f}).")
    return " ".join(msg)

print("\n" + "="*66)
print("🔎 J1 — χ-ABLATION VERDICT")
print("="*66)
print(verdict(res_baseline, res_ablated))
print("All claims are algebraic/model-level; no spacetime signaling implied.")
print("="*66 + "\n")