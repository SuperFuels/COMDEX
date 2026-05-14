#!/usr/bin/env python3
"""
E6-Ω v5c - Enhanced instrumented run with improved burst generation.
Tessaris Photon Algebra Framework (Registry v1.2+)

Key improvements:
  * 2* longer simulation (T=8000) for more bursts
  * Relaxed burst thresholds (easier detection)
  * Increased stochastic forcing for dynamic exploration
  * Lower EMA smoothing for sharper v_S tracking
  * Enhanced CHSH computation with more trials
  * Multi-scale noise injection

Artifacts:
  - backend/modules/knowledge/E6Omega_vS_trace_v5c.json
  - backend/modules/knowledge/E6Omega_v5c_summary.json
  - PAEV_E6Omega_v5c_analysis.png
"""

import json, math
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
#  Constants (Tessaris Registry v1.2)
# ============================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)  # nonlinear coupling term
v_c = math.sqrt(α / Λ)

# ============================================================
#  Enhanced Simulation Parameters
# ============================================================
N = 256
T = 8000
dt = 0.01
base_noise = 0.018

# Controller
kappa_var = 0.03
kappa_var_max = 0.22
theta = 1.2
eta_up = 0.22
eta_dn = 0.04

EMA_ALPHA = 0.35
BURST_TH = 1.3
BURST_MIN = 4

# CHSH angles
a, ap, b, bp = 0.0, np.pi / 4, np.pi / 8, 3 * np.pi / 8

rng = np.random.default_rng(42)

# ============================================================
#  Evolution and Utility Functions
# ============================================================
def evolve_step(state, kappa_var, noise, t):
    """Enhanced evolution with multi-scale stochastic forcing"""
    x = state
    lap = np.roll(x, -1) - 2 * x + np.roll(x, 1)
    fast_noise = noise * rng.normal(0, 1, len(x))
    slow_noise = 0.5 * noise * np.sin(2 * np.pi * t / 500) * rng.normal(0, 0.5, len(x))
    curvature_noise = rng.normal(0, kappa_var * 0.15, len(x))
    x = x + dt * (α * lap - Λ * x) + fast_noise + slow_noise + curvature_noise
    x += 0.005 * np.sin(2 * np.pi * t / 1000) * rng.normal(0, 0.3, len(x))
    return x

def entropy_of(x):
    hist, _ = np.histogram(np.abs(x), bins=64, density=True)
    p = hist[hist > 0]
    return float(-(p * np.log(p)).sum()) if len(p) else 0.0

def msd_of(ref, x):
    diff = x - ref
    return float(np.mean(diff * diff))

def spin_outcome(angle, hidden_phase):
    val = math.cos(hidden_phase - angle)
    p = 0.5 * (1.0 + val)
    return 1 if rng.random() < p else -1

def true_chsh(a, ap, b, bp, hidden_phase):
    def corr(Aang, Bang):
        trials = 200
        s = 0
        for _ in range(trials):
            hp = hidden_phase + rng.normal(0, 0.04)
            A = spin_outcome(Aang, hp)
            B = spin_outcome(Bang, hp + rng.normal(0, 0.04))
            s += A * B
        return s / trials
    Eab = corr(a, b)
    Eabp = corr(a, bp)
    Eapb = corr(ap, b)
    Eapbp = corr(ap, bp)
    return Eab + Eabp + Eapb - Eapbp

# ============================================================
#  Run Simulation
# ============================================================
x = rng.normal(0, 1.0, N)
x0 = x.copy()
S_hist, D_hist, S_CHSH_hist = [], [], []
vs_hist, vs_over_vc_hist, kappa_var_hist = [], [], []
bursts = []
ema_dS, ema_dD = 0.0, 0.0
burst_run = 0
hidden_phase = 0.0

S_prev, D_prev = entropy_of(x), msd_of(x0, x)

for t in range(1, T + 1):
    x = evolve_step(x, kappa_var, base_noise, t)
    hidden_phase += rng.normal(0, 0.025)
    S = entropy_of(x)
    D = msd_of(x0, x)

    dS = (S - S_prev) / dt
    dD = (D - D_prev) / dt
    ema_dS = EMA_ALPHA * dS + (1 - EMA_ALPHA) * ema_dS
    ema_dD = EMA_ALPHA * dD + (1 - EMA_ALPHA) * ema_dD
    vS = ema_dS / (ema_dD + 1e-12)
    vS_over_vc = vS / v_c
    S_chsh = true_chsh(a, ap, b, bp, hidden_phase)

    S_hist.append(S)
    D_hist.append(D)
    vs_hist.append(vS)
    vs_over_vc_hist.append(vS_over_vc)
    S_CHSH_hist.append(S_chsh)
    kappa_var_hist.append(kappa_var)

    if vS_over_vc > theta:
        kappa_var = min(kappa_var * (1 + eta_up), kappa_var_max)
    else:
        kappa_var = max(0.015, kappa_var * (1 - eta_dn))

    if vS_over_vc > BURST_TH:
        burst_run += 1
    else:
        if burst_run >= BURST_MIN:
            bursts.append({"t_start": t - burst_run, "t_end": t, "len": burst_run})
        burst_run = 0

    S_prev, D_prev = S, D

if burst_run >= BURST_MIN:
    bursts.append({"t_start": T - burst_run + 1, "t_end": T, "len": burst_run})

# ============================================================
#  Save Trace JSON
# ============================================================
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
trace_path = Path("backend/modules/knowledge/E6Omega_vS_trace_v5c.json")

trace = {
    "constants": const,
    "params": {
        "N": N, "T": T, "dt": dt, "base_noise": base_noise,
        "controller": {
            "theta": theta,
            "eta_up": eta_up,
            "eta_dn": eta_dn,
            "kappa_var_max": kappa_var_max,
            "kappa_var_init": 0.03
        },
        "ema_alpha": EMA_ALPHA,
        "burst": {"th": BURST_TH, "min_len": BURST_MIN}
    },
    "v_c": v_c,
    "time": [i * dt for i in range(1, T + 1)],
    "S": S_hist,
    "MSD": D_hist,
    "v_S": vs_hist,
    "v_S_over_v_c": vs_over_vc_hist,
    "S_CHSH": S_CHSH_hist,
    "kappa_var": kappa_var_hist,
    "bursts": bursts,
    "timestamp": timestamp
}
trace_path.write_text(json.dumps(trace, indent=2))

# ============================================================
#  Visualization
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
ax1, ax2 = axes

ax1.scatter(vs_over_vc_hist, S_CHSH_hist, s=4, alpha=0.3, c='tab:blue')
ax1.axvline(1.0, ls="--", lw=1, color='gray', label='v_c (diffusion)')
ax1.axvline(BURST_TH, ls="--", lw=1, color='red', label=f'Burst threshold ({BURST_TH})')
ax1.axhline(2.0, ls="--", lw=1, color='green', alpha=0.5, label='Classical limit')
ax1.set_xlabel("v_S / v_c")
ax1.set_ylabel("S_CHSH")
ax1.set_title(f"E6-Ω v5c - v_S bursts vs S_CHSH ({len(bursts)} bursts)")
ax1.legend(fontsize=8)
ax1.grid(alpha=0.3)

t_arr = np.array([i * dt for i in range(1, T + 1)])
ax2.plot(t_arr, vs_over_vc_hist, linewidth=0.5, alpha=0.7, color='purple', label='v_S/v_c')
ax2.axhline(BURST_TH, ls='--', lw=1, color='red', alpha=0.5)
for b in bursts:
    t_start, t_end = (b["t_start"] - 1) * dt, (b["t_end"] - 1) * dt
    ax2.axvspan(t_start, t_end, alpha=0.2, color='orange')
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("v_S / v_c")
ax2.set_title("v_S/v_c Timeline (orange = burst windows)")
ax2.legend(fontsize=8)
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("PAEV_E6Omega_v5c_analysis.png", dpi=200)
plt.close()

# ============================================================
#  Summary JSON
# ============================================================
summary = {
    "constants": const,
    "params": {
        "N": N, "T": T, "dt": dt, "base_noise": base_noise,
        "controller": {
            "theta": theta,
            "eta_up": eta_up,
            "eta_dn": eta_dn,
            "kappa_var_max": kappa_var_max
        },
        "EMA_ALPHA": EMA_ALPHA,
        "enhancements": [
            "2* simulation duration (T=8000)",
            "50% higher base noise (0.018)",
            "Relaxed burst threshold (1.3)",
            "Multi-scale noise injection",
            "Enhanced CHSH trials (200)"
        ]
    },
    "results": {
        "v_c": v_c,
        "S_CHSH_stats": {
            "mean": float(np.mean(S_CHSH_hist)),
            "std": float(np.std(S_CHSH_hist)),
            "max": float(np.max(S_CHSH_hist)),
            "min": float(np.min(S_CHSH_hist)),
            "p95": float(np.percentile(S_CHSH_hist, 95)),
            "p50": float(np.median(S_CHSH_hist))
        },
        "v_S_stats": {
            "mean": float(np.mean(vs_over_vc_hist)),
            "max": float(np.max(vs_over_vc_hist)),
            "p95": float(np.percentile(vs_over_vc_hist, 95))
        },
        "bursts_detected": {
            "count": len(bursts),
            "total_duration_steps": sum(b["len"] for b in bursts),
            "list": bursts[:10]
        },
        "burst_rate": len(bursts) / (T / 1000)
    },
    "files": {
        "trace": str(trace_path),
        "analysis": "PAEV_E6Omega_v5c_analysis.png"
    },
    "timestamp": timestamp,
    "discovery_notes": [
        f"Enhanced run generated {len(bursts)} bursts (vs 1 in v5b).",
        "Multi-scale forcing and relaxed thresholds improve burst statistics.",
        "Ready for I5c correlation analysis with sufficient events.",
        "All claims pertain to Tessaris algebra; no spacetime signaling implied."
    ]
}

Path("backend/modules/knowledge/E6Omega_v5c_summary.json").write_text(json.dumps(summary, indent=2))

# ============================================================
#  Console Output
# ============================================================
print("\n" + "=" * 70)
print("🔥 E6-Ω v5c - ENHANCED INSTRUMENTED RUN COMPLETE")
print("=" * 70)
print(f"Duration:        {T} steps ({T*dt:.0f}s)")
print(f"Bursts detected: {len(bursts)} (vs 1 in v5b)")
print(f"Burst rate:      {len(bursts) / (T/1000):.2f} per 1000 steps")
print(f"S_CHSH range:    [{np.min(S_CHSH_hist):.3f}, {np.max(S_CHSH_hist):.3f}]")
print(f"S_CHSH mean:     {np.mean(S_CHSH_hist):.3f} ± {np.std(S_CHSH_hist):.3f}")
print(f"v_S/v_c max:     {np.max(vs_over_vc_hist):.2f}")
print("=" * 70)
print("✅ Trace saved   -> backend/modules/knowledge/E6Omega_vS_trace_v5c.json")
print("✅ Summary saved -> backend/modules/knowledge/E6Omega_v5c_summary.json")
print("✅ Analysis plot -> PAEV_E6Omega_v5c_analysis.png")
print("=" * 70)
print("\n🎯 Next: Run I5c burst correlation analysis on this trace")
print("   PYTHONPATH=. python backend/photon_algebra/tests/paev_test_I5c_burst_correlation.py")
print("=" * 70 + "\n")