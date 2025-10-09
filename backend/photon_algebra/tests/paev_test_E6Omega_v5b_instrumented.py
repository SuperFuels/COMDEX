#!/usr/bin/env python3
"""
I5c — Enhanced Burst-Aligned v_S ↦ S_CHSH Correlation Analysis
Works with E6-Ω v5c enhanced trace with multiple bursts.

Enhancements:
  • Multi-burst robust correlation (Spearman, Kendall)
  • Event-triggered window analysis pre/post bursts
  • Lag correlation (to detect delayed response)
  • Bootstrap confidence intervals
  • Burst-by-burst diagnostics
  • Dynamic run-type detection (v5b/v5c)
  • Auto-timestamped output files
  • Adaptive parameter injection (from environment)
  • Optional trace regeneration per run

Artifacts:
  - backend/modules/knowledge/I5c_burst_corr.json
  - PAEV_I5c_<run_type>_analysis_<timestamp>.png
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, kendalltau

# ============================================================
#  Optional Trace Regeneration (for adaptive/meta-analysis)
# ============================================================
seed_env = os.getenv("TESSARIS_SEED")
base_noise_env = os.getenv("TESSARIS_BASE_NOISE")
burst_th_env = os.getenv("TESSARIS_BURST_TH")

if seed_env or base_noise_env or burst_th_env:
    print("♻️  Regenerating E6Ω v5c trace with adaptive parameters...")
    env = dict(os.environ)
    subprocess.run(
        ["python", "backend/photon_algebra/tests/paev_test_I5b_burst_correlation.py"],
        env=env,
        check=True
    )
    print("✅ Regeneration complete.\n")

# ============================================================
#  Load Trace (Enhanced w/ fallback)
# ============================================================
TRACE_PATHS = [
    Path("backend/modules/knowledge/E6Omega_vS_trace_v5c.json"),  # enhanced preferred
    Path("backend/modules/knowledge/E6Omega_vS_trace.json"),      # fallback (legacy)
]
TRACE_PATH = next((p for p in TRACE_PATHS if p.exists()), None)

if TRACE_PATH is None:
    print("❌ Error: No valid trace file found.")
    print("💡 Run E6-Ω v5c test first or enable regeneration.")
    exit(1)

TRACE = json.loads(TRACE_PATH.read_text())
print(f"📂 Loaded trace from: {TRACE_PATH}")

# Detect run type from filename
run_type = "v5c" if "v5c" in TRACE_PATH.name else "v5b"

# Extract arrays safely
t = np.array(TRACE.get("time", []))
vsr = np.array(TRACE.get("v_S_over_v_c", []))
S = np.array(TRACE.get("S_CHSH", []))
bursts = TRACE.get("bursts", [])
C = TRACE.get("constants", {})

# Validate
if len(t) == 0 or len(vsr) == 0 or len(S) == 0:
    print("❌ Error: Trace missing essential data ('time', 'v_S_over_v_c', 'S_CHSH').")
    exit(1)

dt = float(t[1] - t[0]) if len(t) > 1 else 0.01
burst_rate = len(bursts) / (len(t) / 1000)
print(f"✅ Trace length: {len(t)} steps ({len(bursts)} bursts, rate={burst_rate:.2f}/1000)")

# ============================================================
#  Global Correlation
# ============================================================
rho, rho_p = spearmanr(vsr, S)
tau, tau_p = kendalltau(vsr, S)

print(f"📈 Global correlations:")
print(f"   Spearman ρ = {rho:.4f} (p = {rho_p:.4f})")
print(f"   Kendall τ  = {tau:.4f} (p = {tau_p:.4f})")

# ============================================================
#  Event-Triggered Averaging
# ============================================================
W_PRE, W_POST = 50, 100
pre_vals, post_vals, burst_details = [], [], []

for b in bursts:
    t_start, te, L = b["t_start"], b["t_end"], b["len"]
    pre_idx = slice(max(0, t_start - W_PRE), t_start)
    post_idx = slice(te, min(len(S), te + W_POST))
    pre, post = S[pre_idx], S[post_idx]

    if len(pre) >= 10 and len(post) >= 10:
        pre_mean, post_mean = float(np.mean(pre)), float(np.mean(post))
        delta = post_mean - pre_mean
        pre_vals.append(pre_mean)
        post_vals.append(post_mean)
        burst_details.append({
            "t_start": int(t_start),
            "t_end": int(te),
            "length": int(L),
            "S_pre": pre_mean,
            "S_post": post_mean,
            "delta_S": delta
        })

pre_vals, post_vals = np.array(pre_vals), np.array(post_vals)
delta = post_vals - pre_vals if len(pre_vals) > 0 else np.array([])

print(f"\n🎯 Event analysis: {len(delta)} valid bursts | ΔS = {np.mean(delta):.4f} ± {np.std(delta):.4f}")

# ============================================================
#  Permutation Test
# ============================================================
N_PERM = 3000
obs = float(np.mean(delta)) if delta.size else 0.0
if delta.size >= 3:
    rng = np.random.default_rng(0)
    perms = [np.mean(delta * rng.choice([-1, 1], size=delta.size)) for _ in range(N_PERM)]
    p_perm = float(np.mean(np.abs(perms) >= abs(obs)))
else:
    p_perm = 1.0
print(f"   Permutation p-value: {p_perm:.4f}")

# ============================================================
#  Lag Correlation
# ============================================================
max_lag = 50
lags = range(-max_lag, max_lag + 1)
lag_corrs = []
for lag in lags:
    if lag < 0:
        corr_pair = (vsr[:lag], S[-lag:])
    elif lag > 0:
        corr_pair = (vsr[lag:], S[:-lag])
    else:
        corr_pair = (vsr, S)
    if len(corr_pair[0]) > 100:
        r, _ = spearmanr(*corr_pair)
        lag_corrs.append(r)
    else:
        lag_corrs.append(np.nan)

lag_corrs = np.array(lag_corrs)
best_lag_idx = np.nanargmax(np.abs(lag_corrs))
best_lag = list(lags)[best_lag_idx]
best_corr = lag_corrs[best_lag_idx]
print(f"⏱️  Lag analysis: best at {best_lag} steps ({best_lag*dt:.2f}s), ρ={best_corr:.4f}")

# ============================================================
#  Bootstrap CI
# ============================================================
N_BOOT = 1000
if len(delta) >= 3:
    rng = np.random.default_rng(1)
    boot_means = [np.mean(rng.choice(delta, size=len(delta), replace=True)) for _ in range(N_BOOT)]
    ci_low, ci_high = np.percentile(boot_means, [2.5, 97.5])
else:
    ci_low, ci_high = np.nan, np.nan

# ============================================================
#  Visualization
# ============================================================
timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
fig_path = f"PAEV_I5c_{run_type}_analysis_{timestamp}.png"
fig = plt.figure(figsize=(15, 5))
plt.subplot(1, 3, 1)
if len(pre_vals) > 0:
    plt.scatter(pre_vals, post_vals, alpha=0.7, s=80, c='tab:blue', edgecolors='black')
    lim = [min(pre_vals.min(), post_vals.min()), max(pre_vals.max(), post_vals.max())]
    plt.plot(lim, lim, 'k--', lw=1.5)
    plt.title("Pre vs Post S_CHSH")
plt.subplot(1, 3, 3)
plt.plot(np.array(list(lags)) * dt, lag_corrs, 'purple')
plt.axvline(best_lag * dt, ls='--', color='red')
plt.tight_layout()
plt.savefig(fig_path, dpi=200)
print(f"✅ Plot saved → {fig_path}")

# ============================================================
#  Save Summary
# ============================================================
summary = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "source_trace": str(TRACE_PATH),
    "run_type": run_type,
    "params": {
        "window_steps": {"pre": W_PRE, "post": W_POST},
        "dt": dt,
        "permutations": N_PERM,
        "bootstrap_samples": N_BOOT,
        "max_lag": max_lag,
    },
    "results": {
        "spearman_rho": float(rho),
        "spearman_p": float(rho_p),
        "kendall_tau": float(tau),
        "kendall_p": float(tau_p),
        "delta_S_mean": float(obs),
        "permutation_p": float(p_perm),
        "best_lag": int(best_lag),
        "correlation_best_lag": float(best_corr),
        "bootstrap_ci": [float(ci_low), float(ci_high)] if not np.isnan(ci_low) else None,
    },
    "files": {"figure": fig_path},
    "discovery_notes": [
        f"Global ρ={rho:.3f} (p={rho_p:.3f}), ΔS={obs:.3f}, lag={best_lag*dt:.2f}s",
        "All effects remain within Tessaris algebraic domain; not physically demonstrated.",
    ],
}
Path("backend/modules/knowledge/I5c_burst_corr.json").write_text(json.dumps(summary, indent=2))
print("✅ Summary saved → backend/modules/knowledge/I5c_burst_corr.json")

print("\n======================================================================")
print("🔬 I5c — ENHANCED BURST-CORRELATION ANALYSIS COMPLETE")
print("======================================================================")
print(f"Global ρ={rho:.4f}, ΔS={obs:.4f}, lag={best_lag*dt:.2f}s, p_perm={p_perm:.4f}")
print("======================================================================\n")