#!/usr/bin/env python3
"""
J4 — α-ablation study (baseline α vs α=0)
-----------------------------------------
Tests the role of α (diffusion coefficient) in sustaining transport and
entropy–MSD coupling. Completes the J-series minimal-term ablations.

Outputs
-------
- backend/modules/knowledge/J4_ablation_alpha_summary.json
- PAEV_J4_ablation_alpha.png

Notes
-----
All results are algebraic/model-level only; no physical signaling implied.
"""

import json, math, os
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
#  Unified Constants Loader
# ============================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)  # ✅ fallback added
C = const
v_c = math.sqrt(max(α / Λ, 1e-9))

# ============================================================
#  Environment Configuration
# ============================================================
SEED = int(os.getenv("TESSARIS_SEED", "4044"))
N = int(os.getenv("TESSARIS_N", "256"))
T = int(os.getenv("TESSARIS_T", "8000"))
DT = float(os.getenv("TESSARIS_DT", "0.01"))
BASE_NOISE = float(os.getenv("TESSARIS_BASE_NOISE", "0.018"))
EMA_ALPHA = float(os.getenv("TESSARIS_EMA", "0.30"))
BURST_TH = float(os.getenv("TESSARIS_BURST_TH", "1.15"))
BURST_MIN = int(os.getenv("TESSARIS_BURST_MIN", "5"))

rng = np.random.default_rng(SEED)

print("\n🧩 J4 Configuration:")
print(f"   base_noise={BASE_NOISE}, BURST_TH={BURST_TH}")
print(f"   seed={SEED}, steps={T}, dt={DT}")
print(f"   Constants → ħ={ħ}, G={G}, Λ={Λ}, α={α}, β={β}, χ={χ}")
print("------------------------------------------------------------")

# ============================================================
#  Helper Functions
# ============================================================
def entropy_of(x):
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    hist, _ = np.histogram(np.abs(x), bins=64, density=True)
    p = hist[hist > 0]
    return float(-(p * np.log(p)).sum()) if len(p) else 0.0

def msd_of(ref, x):
    d = x - ref
    return float(np.mean(d * d))

def evolve_step(x, alpha_coeff, noise_scale):
    lap = np.roll(x, -1) - 2 * x + np.roll(x, 1)
    x = np.clip(x, -50, 50)
    chi_term = χ * np.clip(x * x * x, -1e3, 1e3)
    beta_term = -β * x
    x = x + DT * (alpha_coeff * lap - Λ * x + chi_term + beta_term)
    x += noise_scale * rng.normal(0, 1, len(x))
    return x

# ============================================================
#  Paired Run Function
# ============================================================
def run_config(alpha_coeff, label):
    rng = np.random.default_rng(SEED)
    x = rng.normal(0, 1.0, N)
    x0 = x.copy()

    S_hist, D_hist, vsr_hist = [], [], []
    ema_dS = ema_dD = 0.0
    bursts, runlen = [], 0
    S_prev, D_prev = entropy_of(x), msd_of(x0, x)

    for t in range(1, T + 1):
        x = evolve_step(x, alpha_coeff, BASE_NOISE)
        S, D = entropy_of(x), msd_of(x0, x)

        dS, dD = (S - S_prev) / DT, (D - D_prev) / DT
        ema_dS = EMA_ALPHA * dS + (1 - EMA_ALPHA) * ema_dS
        ema_dD = EMA_ALPHA * dD + (1 - EMA_ALPHA) * ema_dD
        vS = ema_dS / (ema_dD + 1e-12)
        vsr = vS / v_c

        S_hist.append(S)
        D_hist.append(D)
        vsr_hist.append(vsr)

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

    # Scaling Exponents
    tgrid = np.arange(1, T + 1) * DT
    mid = slice(T // 4, T // 4 * 3)
    y, xlog = np.log(np.maximum(1e-12, np.array(D_hist)[mid])), np.log(tgrid[mid])
    p = float(np.polyfit(xlog, y, 1)[0])
    Dh, Sh = np.array(D_hist), np.array(S_hist)
    valid = Dh > 0
    nu = float(np.polyfit(np.log(Dh[valid]), np.log(Sh[valid]), 1)[0]) if valid.sum() > 10 else float("nan")

    return {
        "label": label,
        "alpha": alpha_coeff,
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

# ============================================================
#  Paired Runs
# ============================================================
res_baseline = run_config(alpha_coeff=α, label=f"baseline_α={α}")
res_zero = run_config(alpha_coeff=0.0, label="α=0 (no diffusion)")

# ============================================================
#  Visualization
# ============================================================
plt.figure(figsize=(13, 5))
ax1 = plt.subplot(1, 2, 1)
labels = [f"α={α}", "α=0"]
p_vals, nu_vals = [res_baseline["p"], res_zero["p"]], [res_baseline["nu"], res_zero["nu"]]
x = np.arange(2); w = 0.35
ax1.bar(x - w / 2, p_vals, w, label="p (transport)")
ax1.bar(x + w / 2, nu_vals, w, label="ν (entropy↔MSD)")
ax1.set_xticks(x); ax1.set_xticklabels(labels)
ax1.set_ylabel("Exponent value")
ax1.set_title("J4 — Exponents under α ablation")
ax1.legend(); ax1.grid(alpha=0.3)

ax2 = plt.subplot(1, 2, 2)
b1, b2 = [b["len"] for b in res_baseline["bursts"]], [b["len"] for b in res_zero["bursts"]]
ax2.hist(b1, bins=15, alpha=0.6, label=f"α={α} (n={len(b1)})")
ax2.hist(b2, bins=15, alpha=0.6, label=f"α=0 (n={len(b2)})")
ax2.set_xlabel("Burst length (steps)")
ax2.set_ylabel("Count")
ax2.set_title("J4 — v_S/v_c bursts")
ax2.legend(); ax2.grid(alpha=0.3)
plt.tight_layout()
fig_path = "PAEV_J4_ablation_alpha.png"
plt.savefig(fig_path, dpi=200)
print(f"✅ Figure saved → {fig_path}")

# ============================================================
#  JSON Summary
# ============================================================
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
summary = {
    "timestamp": ts,
    "seed": SEED,
    "constants": const,
    "params": {
        "N": N, "T": T, "dt": DT, "base_noise": BASE_NOISE,
        "ema_alpha": EMA_ALPHA, "burst_th": BURST_TH, "burst_min": BURST_MIN
    },
    "results": {
        "baseline": res_baseline,
        "alpha_zero": res_zero,
        "comparison": {
            "Δp": res_zero["p"] - res_baseline["p"],
            "Δnu": res_zero["nu"] - res_baseline["nu"],
            "Δbursts": res_zero["stats"]["bursts_count"] - res_baseline["stats"]["bursts_count"]
        }
    },
    "files": {"figure": fig_path}
}
out_path = Path("backend/modules/knowledge/J4_ablation_alpha_summary.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"✅ Summary saved → {out_path}")

# ============================================================
#  Verdict
# ============================================================
def verdict(r0, r1):
    msg = []
    if r1["stats"]["bursts_count"] < r0["stats"]["bursts_count"]:
        msg.append("Removing α halts diffusion — reduced transport observed.")
    elif r1["stats"]["bursts_count"] > r0["stats"]["bursts_count"]:
        msg.append("Without α, instability grows → diffusion stabilizes dynamics.")
    else:
        msg.append("No burst difference — equilibrium regime.")
    dp, dn = r1["p"] - r0["p"], r1["nu"] - r0["nu"]
    if abs(dp) < 0.02:
        msg.append("Transport exponent p ~ invariant (possible frozen field).")
    else:
        msg.append(f"Transport exponent shift Δp={dp:.3f}.")
    if abs(dn) > 0.1:
        msg.append(f"Entropy–MSD coupling changed (Δν={dn:.3f}).")
    return " ".join(msg)

print("\n" + "=" * 66)
print("🔎 J4 — α-ABLATION VERDICT")
print("=" * 66)
print(verdict(res_baseline, res_zero))
print("All claims are algebraic/model-level; no spacetime signaling implied.")
print("=" * 66 + "\n")