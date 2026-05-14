#!/usr/bin/env python3
"""
PAEV Test I5c - Enhanced Burst-Aligned v_S ↦ S_CHSH Correlation Analysis
Tessaris Photon Algebra Framework (v1.0+ Registry Aligned)

Works with E6-Ω v5c enhanced trace with multiple bursts.

Enhancements:
  * Multi-burst robust correlation (Spearman, Kendall)
  * Event-triggered window analysis pre/post bursts
  * Lag correlation (to detect delayed response)
  * Bootstrap confidence intervals
  * Burst-by-burst diagnostics
  * Dynamic run-type detection (v5b/v5c)
  * Auto-timestamped output files
  * Clean reproducibility and adaptive parameter summary
  * Optional regeneration if adaptive environment is set

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
#  🔹 Load Tessaris constants (auto-synced from registry)
# ============================================================
from backend.photon_algebra.utils.load_constants import load_constants
REGISTRY_CONST = load_constants()
ħ = REGISTRY_CONST.get("ħ", 1e-3)
G = REGISTRY_CONST.get("G", 1e-5)
Λ = REGISTRY_CONST.get("Λ", 1e-6)
α = REGISTRY_CONST.get("α", 0.5)
β = REGISTRY_CONST.get("β", 0.2)
χ = REGISTRY_CONST.get("χ", 1.0)

# ============================================================
#  Optional Trace Regeneration (Adaptive Runs)
# ============================================================
base_noise_env = os.getenv("TESSARIS_BASE_NOISE")
burst_th_env = os.getenv("TESSARIS_BURST_TH")
seed_env = os.getenv("TESSARIS_SEED")

if base_noise_env or burst_th_env or seed_env:
    print("♻️  Regenerating E6Ω v5c trace with adaptive parameters...")
    env = dict(os.environ)
    try:
        subprocess.run(
            ["python", "backend/photon_algebra/tests/paev_test_E6Omega_v5c.py"],
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Trace regeneration complete.\n")
    except subprocess.CalledProcessError as e:
        print("❌ Regeneration failed:")
        print(e.stdout)
        print(e.stderr)
        exit(1)

# ============================================================
#  Load Trace (Enhanced w/ Fallback)
# ============================================================
TRACE_PATHS = [
    Path("backend/modules/knowledge/E6Omega_vS_trace_v5c.json"),
    Path("backend/modules/knowledge/E6Omega_vS_trace.json"),
]
TRACE_PATH = next((p for p in TRACE_PATHS if p.exists()), None)

if TRACE_PATH is None:
    print("❌ Error: No valid trace file found.")
    print("💡 Run the E6-Ω v5c generator or enable regeneration.")
    exit(1)

TRACE = json.loads(TRACE_PATH.read_text())
print(f"📂 Loaded trace from: {TRACE_PATH}")

run_type = "v5c" if "v5c" in TRACE_PATH.name else "v5b"

# ============================================================
#  Extract Data
# ============================================================
t = np.array(TRACE.get("time", []))
vsr = np.array(TRACE.get("v_S_over_v_c", []))
S = np.array(TRACE.get("S_CHSH", []))
bursts = TRACE.get("bursts", [])
C = TRACE.get("constants", {}) or REGISTRY_CONST
params = TRACE.get("params", {})

if len(t) == 0 or len(vsr) == 0 or len(S) == 0:
    print("❌ Error: Trace missing essential data ('time', 'v_S_over_v_c', 'S_CHSH').")
    exit(1)

dt = float(t[1] - t[0]) if len(t) > 1 else 0.01
burst_rate = len(bursts) / (len(t) / 1000)
print(f"✅ Trace length: {len(t)} steps ({len(bursts)} bursts, rate={burst_rate:.2f}/1000)")

# ============================================================
#  Inject Adaptive Parameters (Non-Destructive)
# ============================================================
if base_noise_env or burst_th_env or seed_env:
    print("🧩 Applying adaptive overrides:")
    params.setdefault("controller", {})
    if base_noise_env:
        params["base_noise"] = float(base_noise_env)
        print(f"   base_noise = {base_noise_env}")
    if burst_th_env:
        params["controller"]["BURST_TH"] = float(burst_th_env)
        print(f"   BURST_TH   = {burst_th_env}")
    if seed_env:
        np.random.seed(int(seed_env))
        params["seed"] = int(seed_env)
        print(f"   seed       = {seed_env}")
    print("--------------------------------------------------\n")

# ============================================================
#  Global Correlations
# ============================================================
rho, rho_p = spearmanr(vsr, S)
tau, tau_p = kendalltau(vsr, S)
print(f"📈 Global correlations:\n   Spearman ρ = {rho:.4f} (p = {rho_p:.4f})\n   Kendall τ  = {tau:.4f} (p = {tau_p:.4f})")

# ============================================================
#  Event-Triggered Analysis (Pre/Post Burst)
# ============================================================
W_PRE, W_POST = 50, 100
pre_vals, post_vals, burst_details = [], [], []

for b in bursts:
    t_start, te, L = b["t_start"], b["t_end"], b["len"]
    pre_idx = slice(max(0, t_start - W_PRE), t_start)
    post_idx = slice(te, min(len(S), te + W_POST))
    pre, post = S[pre_idx], S[post_idx]
    if len(pre) >= 10 and len(post) >= 10:
        pre_m, post_m = float(np.mean(pre)), float(np.mean(post))
        pre_vals.append(pre_m)
        post_vals.append(post_m)
        burst_details.append({
            "t_start": int(t_start),
            "t_end": int(te),
            "length": int(L),
            "S_pre": pre_m,
            "S_post": post_m,
            "delta_S": float(post_m - pre_m)
        })

delta = np.array(post_vals) - np.array(pre_vals)
obs = float(np.mean(delta)) if len(delta) > 0 else 0.0
print(f"\n🎯 Event analysis: {len(delta)} valid bursts | ΔS = {obs:.4f} ± {np.std(delta):.4f}")

# ============================================================
#  Permutation Significance
# ============================================================
N_PERM = 3000
if len(delta) >= 3:
    rng = np.random.default_rng(0)
    perms = [np.mean(delta * rng.choice([-1, 1], size=len(delta))) for _ in range(N_PERM)]
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
best_idx = np.nanargmax(np.abs(lag_corrs))
best_lag, best_corr = list(lags)[best_idx], lag_corrs[best_idx]
print(f"⏱️  Lag analysis: best lag = {best_lag} steps ({best_lag*dt:.2f}s), ρ={best_corr:.4f}")

# ============================================================
#  Bootstrap Confidence Interval
# ============================================================
N_BOOT = 1000
if len(delta) >= 3:
    rng = np.random.default_rng(1)
    boot_means = [np.mean(rng.choice(delta, len(delta), replace=True)) for _ in range(N_BOOT)]
    ci_low, ci_high = np.percentile(boot_means, [2.5, 97.5])
else:
    ci_low, ci_high = np.nan, np.nan
print(f"📊 Bootstrap 95% CI for ΔS: [{ci_low:.4f}, {ci_high:.4f}]")

# ============================================================
#  Visualization
# ============================================================
timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
fig_path = f"PAEV_I5c_{run_type}_analysis_{timestamp}.png"

plt.figure(figsize=(14, 4))
plt.subplot(1, 2, 1)
plt.scatter(pre_vals, post_vals, c='tab:blue', edgecolors='k')
plt.xlabel("Pre-burst S_CHSH")
plt.ylabel("Post-burst S_CHSH")
plt.title(f"Pre vs Post ({len(pre_vals)} bursts)")
plt.subplot(1, 2, 2)
plt.plot(np.array(list(lags)) * dt, lag_corrs, 'purple')
plt.axvline(best_lag * dt, ls='--', c='red')
plt.title("Lag Correlation")
plt.tight_layout()
plt.savefig(fig_path, dpi=200)
print(f"✅ Plot saved -> {fig_path}")

# ============================================================
#  Save Summary JSON
# ============================================================
summary = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "constants": C,
    "source_trace": str(TRACE_PATH),
    "run_type": run_type,
    "params": {
        "controller": params.get("controller", {}),
        "base_noise": params.get("base_noise", None),
        "seed": params.get("seed", None),
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
        "delta_S_mean": obs,
        "permutation_p": p_perm,
        "lag_best_steps": best_lag,
        "lag_best_seconds": best_lag * dt,
        "lag_best_rho": best_corr,
        "bootstrap_CI_95": [float(ci_low), float(ci_high)] if not np.isnan(ci_low) else None,
    },
    "files": {"figure": fig_path},
    "discovery_notes": [
        f"Global correlation: ρ={rho:.3f} (p={rho_p:.3f})",
        f"ΔS_mean={obs:.3f} ± {np.std(delta):.3f}",
        f"Lag peak at {best_lag*dt:.2f}s (ρ={best_corr:.3f})",
        "All correlations remain within Tessaris algebraic model; not empirical.",
    ],
}

Path("backend/modules/knowledge/I5c_burst_corr.json").write_text(json.dumps(summary, indent=2))
print("✅ Summary saved -> backend/modules/knowledge/I5c_burst_corr.json")

# ============================================================
#  Console Summary
# ============================================================
print("\n======================================================================")
print("🔬 I5c - ENHANCED BURST-CORRELATION ANALYSIS COMPLETE")
print("======================================================================")
print(f"Source: {TRACE_PATH}")
print(f"Bursts: {len(bursts)}, Valid: {len(delta)}")
print(f"ρ={rho:.4f}, p={rho_p:.4f}, ΔS={obs:.4f}, p_perm={p_perm:.4f}")
print(f"Best lag={best_lag} ({best_lag*dt:.2f}s), ρ={best_corr:.4f}")
print("======================================================================\n")