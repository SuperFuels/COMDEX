#!/usr/bin/env python3
"""
I6 — Multi-Trial Meta-Analysis of v_S ↦ S_CHSH Correlation
===========================================================
Runs multiple E6-Ω v5c simulations with varying RNG seeds and aggregates
their correlation and burst statistics.

Enhancements:
  • Parallel-safe multi-seed reproducibility
  • Comprehensive per-trial statistics (ρ, τ, ΔS, bursts)
  • Confidence intervals and reproducibility test
  • Visualization suite (correlations, ΔS, burst count, forest plot)
  • JSON summary compatible with I7 adaptive pipelines

Artifacts:
  - backend/modules/knowledge/I6_meta_analysis.json
  - PAEV_I6_meta_analysis.png
"""

import json, math
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, kendalltau, ttest_1samp

# ============================================================
#  Tessaris Constants (Registry v1.2)
# ============================================================
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()

ħ = const.get("ħ", 1e-3)
G = const.get("G", 1e-5)
Λ = const.get("Λ", 1e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
χ = const.get("χ", 1.0)
v_c = math.sqrt(α / Λ)

# ============================================================
#  Core E6Ω v5c Trial Runner
# ============================================================
def run_e6omega_trial(seed, T=8000, verbose=False):
    """
    Run one E6Ω v5c-style trace with deterministic random seed.
    Returns (trace_dict, summary_dict).
    """
    # Simulation Parameters
    N = 256
    dt = 0.01
    base_noise = 0.018
    kappa_var = 0.03
    kappa_var_max = 0.22
    theta = 1.2
    eta_up = 0.22
    eta_dn = 0.04
    EMA_ALPHA = 0.35
    BURST_TH = 1.3
    BURST_MIN = 4

    # CHSH Angles
    a, ap, b, bp = 0.0, np.pi / 4, np.pi / 8, 3 * np.pi / 8

    rng = np.random.default_rng(seed)

    # Helper Functions
    def evolve_step(x, kappa_var, noise, t):
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
        return float(np.mean((x - ref) ** 2))

    def spin_outcome(angle, phase):
        val = math.cos(phase - angle)
        p = 0.5 * (1.0 + val)
        return 1 if rng.random() < p else -1

    def true_chsh(a, ap, b, bp, phase):
        def corr(Aang, Bang):
            s = sum(
                spin_outcome(Aang, phase + rng.normal(0, 0.04)) *
                spin_outcome(Bang, phase + rng.normal(0, 0.04))
                for _ in range(200)
            )
            return s / 200
        return corr(a, b) + corr(a, bp) + corr(ap, b) - corr(ap, bp)

    # Initialization
    x = rng.normal(0, 1.0, N)
    x0 = x.copy()
    S_hist, S_CHSH_hist, vs_over_vc_hist = [], [], []
    bursts, ema_dS, ema_dD = [], 0.0, 0.0
    burst_run, hidden_phase = 0, 0.0
    S_prev, D_prev = entropy_of(x), msd_of(x0, x)

    # Evolution Loop
    for t in range(1, T + 1):
        x = evolve_step(x, kappa_var, base_noise, t)
        hidden_phase += rng.normal(0, 0.025)
        S = entropy_of(x)
        D = msd_of(x0, x)
        dS, dD = (S - S_prev) / dt, (D - D_prev) / dt
        ema_dS = EMA_ALPHA * dS + (1 - EMA_ALPHA) * ema_dS
        ema_dD = EMA_ALPHA * dD + (1 - EMA_ALPHA) * ema_dD
        vS = ema_dS / (ema_dD + 1e-12)
        vS_over_vc = vS / v_c
        S_chsh = true_chsh(a, ap, b, bp, hidden_phase)

        S_hist.append(S)
        S_CHSH_hist.append(S_chsh)
        vs_over_vc_hist.append(vS_over_vc)

        # Adaptive variance control
        if vS_over_vc > theta:
            kappa_var = min(kappa_var * (1 + eta_up), kappa_var_max)
        else:
            kappa_var = max(0.015, kappa_var * (1 - eta_dn))

        # Burst detection
        if vS_over_vc > BURST_TH:
            burst_run += 1
        elif burst_run >= BURST_MIN:
            bursts.append({"t_start": t - burst_run, "t_end": t, "len": burst_run})
            burst_run = 0

        S_prev, D_prev = S, D

    if burst_run >= BURST_MIN:
        bursts.append({"t_start": T - burst_run + 1, "t_end": T, "len": burst_run})

    trace = {
        "seed": seed,
        "constants": const,
        "v_S_over_v_c": vs_over_vc_hist,
        "S_CHSH": S_CHSH_hist,
        "bursts": bursts,
    }

    summary = {
        "seed": seed,
        "num_bursts": len(bursts),
        "S_CHSH_mean": float(np.mean(S_CHSH_hist)),
        "S_CHSH_std": float(np.std(S_CHSH_hist)),
    }

    if verbose:
        print(f"  → Seed {seed}: {len(bursts)} bursts | S_mean={summary['S_CHSH_mean']:.3f}")

    return trace, summary


# ============================================================
#  Multi-Trial Meta-Analysis
# ============================================================
N_TRIALS = 5
SEEDS = [42, 123, 456, 789, 1011]
T = 8000

print("\n" + "=" * 70)
print("🔬 I6 — MULTI-TRIAL META-ANALYSIS")
print("=" * 70)
print(f"Running {N_TRIALS} trials across seeds {SEEDS}")
print("=" * 70 + "\n")

trials = []
for seed in SEEDS:
    trace, summary = run_e6omega_trial(seed, T=T, verbose=True)
    vsr = np.array(trace["v_S_over_v_c"])
    S = np.array(trace["S_CHSH"])
    rho, rho_p = spearmanr(vsr, S)
    tau, tau_p = kendalltau(vsr, S)

    # Event-triggered ΔS
    W_PRE, W_POST = 50, 100
    pre_vals, post_vals = [], []
    for b in trace["bursts"]:
        t_start, te = b["t_start"], b["t_end"]
        pre = S[max(0, t_start - W_PRE):t_start]
        post = S[te:min(len(S), te + W_POST)]
        if len(pre) >= 10 and len(post) >= 10:
            pre_vals.append(np.mean(pre))
            post_vals.append(np.mean(post))
    delta_S = float(np.mean(np.array(post_vals) - np.array(pre_vals))) if pre_vals else 0.0

    trials.append({
        "seed": seed,
        "num_bursts": len(trace["bursts"]),
        "S_CHSH_mean": summary["S_CHSH_mean"],
        "S_CHSH_std": summary["S_CHSH_std"],
        "spearman_rho": float(rho),
        "spearman_p": float(rho_p),
        "kendall_tau": float(tau),
        "kendall_p": float(tau_p),
        "delta_S_post_pre": delta_S,
        "num_valid_windows": len(pre_vals),
    })

# ============================================================
#  Aggregate Statistics
# ============================================================
rhos = np.array([t["spearman_rho"] for t in trials])
taus = np.array([t["kendall_tau"] for t in trials])
deltas = np.array([t["delta_S_post_pre"] for t in trials])
bursts = np.array([t["num_bursts"] for t in trials])

meta_stats = {
    "spearman_rho": {k: float(v) for k, v in zip(["mean", "std", "median", "min", "max"],
        [np.mean(rhos), np.std(rhos), np.median(rhos), np.min(rhos), np.max(rhos)])},
    "kendall_tau": {"mean": float(np.mean(taus)), "std": float(np.std(taus)), "median": float(np.median(taus))},
    "delta_S": {"mean": float(np.mean(deltas)), "std": float(np.std(deltas)), "median": float(np.median(deltas))},
    "burst_count": {"mean": float(np.mean(bursts)), "std": float(np.std(bursts)), "total": int(np.sum(bursts))},
}

t_stat, p_val = ttest_1samp(rhos, 0.0)
meta_stats["significance_test"] = {
    "null_hypothesis": "mean(rho)=0",
    "t_statistic": float(t_stat),
    "p_value": float(p_val),
    "interpretation": "Significant" if p_val < 0.05 else "Not significant",
}

# ============================================================
#  Visualization
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
x = np.arange(1, N_TRIALS + 1)

axes[0, 0].bar(x - 0.2, rhos, 0.4, label="Spearman ρ", color="tab:blue", alpha=0.7)
axes[0, 0].bar(x + 0.2, taus, 0.4, label="Kendall τ", color="tab:orange", alpha=0.7)
axes[0, 0].axhline(0, ls="--", lw=1, color="gray")
axes[0, 0].set_title("Trial Correlations", fontweight="bold")
axes[0, 0].legend(); axes[0, 0].grid(alpha=0.3)

axes[0, 1].bar(x, deltas, color="tab:green", edgecolor="black", alpha=0.7)
axes[0, 1].axhline(0, ls="--", lw=1, color="gray")
axes[0, 1].set_title("ΔS (Post–Pre Burst)", fontweight="bold"); axes[0, 1].grid(alpha=0.3)

axes[1, 0].bar(x, bursts, color="tab:purple", alpha=0.7, edgecolor="black")
axes[1, 0].set_title("Burst Counts", fontweight="bold"); axes[1, 0].grid(alpha=0.3)

means = [t["S_CHSH_mean"] for t in trials]
errors = [t["S_CHSH_std"] / np.sqrt(T) for t in trials]
y_pos = np.arange(N_TRIALS)
axes[1, 1].errorbar(means, y_pos, xerr=errors, fmt="o", color="tab:red", ecolor="black", capsize=5)
axes[1, 1].axvline(np.mean(means), ls="--", lw=1.5, color="darkred", alpha=0.6)
axes[1, 1].set_yticks(y_pos); axes[1, 1].set_yticklabels([f"T{i+1}" for i in range(N_TRIALS)])
axes[1, 1].set_title("S_CHSH Mean ± SEM", fontweight="bold"); axes[1, 1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig("PAEV_I6_meta_analysis.png", dpi=200)
print("✅ Figure saved → PAEV_I6_meta_analysis.png\n")

# ============================================================
#  Save Summary
# ============================================================
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
summary = {
    "meta_analysis": "I6 — v_S ↦ S_CHSH Multi-Trial Correlation",
    "constants": const,
    "params": {"n_trials": N_TRIALS, "seeds": SEEDS, "T_per_trial": T},
    "trials": trials,
    "aggregate_statistics": meta_stats,
    "files": {"plot": "PAEV_I6_meta_analysis.png"},
    "timestamp": timestamp,
    "discovery_notes": [
        f"Mean Spearman ρ = {meta_stats['spearman_rho']['mean']:.4f} ± {meta_stats['spearman_rho']['std']:.4f}",
        f"Mean ΔS = {meta_stats['delta_S']['mean']:.4f} ± {meta_stats['delta_S']['std']:.4f}",
        f"Significance: {meta_stats['significance_test']['interpretation']} (p={meta_stats['significance_test']['p_value']:.4f})",
        f"Total bursts: {meta_stats['burst_count']['total']}",
        "All interpretations remain within Tessaris algebraic modeling domain.",
    ],
}
out_path = Path("backend/modules/knowledge/I6_meta_analysis.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"✅ Summary saved → {out_path}")

# ============================================================
#  Console Recap
# ============================================================
print("=" * 70)
print("📊 I6 META-ANALYSIS COMPLETE")
print("=" * 70)
print(f"Trials: {N_TRIALS} | Total bursts: {meta_stats['burst_count']['total']}")
print(f"ρ_mean={meta_stats['spearman_rho']['mean']:.4f} ± {meta_stats['spearman_rho']['std']:.4f}")
print(f"ΔS_mean={meta_stats['delta_S']['mean']:.4f} ± {meta_stats['delta_S']['std']:.4f}")
print(f"Significance: {meta_stats['significance_test']['interpretation']} (p={meta_stats['significance_test']['p_value']:.4f})")
print("=" * 70 + "\n")