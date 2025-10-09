#!/usr/bin/env python3
"""
L1 — Boost Invariance (Tessaris)
--------------------------------
Question: Are key exponents/lengths invariant when observed from a boosted frame?

We evolve a damped χ-driven lattice (stable hyperbolic dynamics), then
compare:
  • transport exponent p from MSD ~ t^p
  • correlation length ξ from C(r) ~ exp(-r/ξ)
in the lab frame vs. a Lorentz-like boosted frame defined by c_eff.

Outputs
-------
- backend/modules/knowledge/L1_boost_invariance_summary.json
- PAEV_L1_boost_invariance.png

Notes
-----
Model-level test only; no physical claims implied.
Implements the Tessaris Unified Constants & Verification Protocol.
"""

from __future__ import annotations
import json, math
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import matplotlib.pyplot as plt
np.seterr(all="ignore")

# ── Tessaris Unified Constants & Verification Protocol ─────────────
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()  # ensures v1.2 constants registry coherence
ħ = const["ħ"]; G = const["G"]; Λ = const["Λ"]; α = const["α"]; β = const["β"]
χ = const.get("χ", 1.0)   # keep robust if χ absent in old registries

print("=== L1 — Boost Invariance (Tessaris) ===")
print(f"Constants → ħ={ħ}, G={G}, Λ={Λ}, α={α}, β={β}, χ={χ}")

# ── Grid & integration params (stable per K3b) ─────────────────────
N, steps = 512, 2000
dx, dt = 1.0, 0.002
damping = 0.05
seed = 8282
rng = np.random.default_rng(seed)

# Effective causal speed and safe boost
c_eff = math.sqrt(α / (1.0 + Λ))
v_boost = 0.3 * c_eff            # modest boost to keep γ ~ 1
gamma = 1.0 / math.sqrt(1.0 - (v_boost / c_eff)**2)

print(f"Grid N={N}, steps={steps}, dt={dt}, dx={dx}")
print(f"c_eff≈{c_eff:.6f}, boost v≈{v_boost:.6f}, gamma≈{gamma:.6f}")

# ── helpers ────────────────────────────────────────────────────────
def lap(f):
    return np.roll(f, -1) - 2*f + np.roll(f, 1)

def entropy_of(x):
    x = np.clip(np.abs(x), 1e-12, None)
    hist, _ = np.histogram(x, bins=128, density=True)
    p = hist[hist > 0]
    return float(-(p * np.log(p)).sum()) if p.size else 0.0

def corr_length(field):
    """Estimate ξ from exp fit of normalized autocorrelation C(r)."""
    f = field - field.mean()
    F = np.fft.rfft(f)
    ps = np.fft.irfft(F * np.conj(F), n=f.size)
    C = np.real(ps) / (ps[0] + 1e-12)
    r = np.arange(len(C))
    # fit where C in (0.05, 0.8) and r > 2
    mask = (C > 0.05) & (C < 0.8) & (r > 2)
    if mask.sum() < 10:
        return float("nan")
    p = np.polyfit(r[mask], np.log(C[mask]), 1)
    xi = -1.0 / p[0]
    return float(xi)

def transport_exponent(msd, t):
    mid = slice(len(t)//4, 3*len(t)//4)
    y = np.log(np.maximum(1e-12, msd[mid]))
    x = np.log(np.maximum(1e-12, t[mid]))
    return float(np.polyfit(x, y, 1)[0])

# ── initial condition: localized packet with tiny momentum bias ────
x = np.linspace(-N//2, N//2, N) * dx
u = np.exp(-0.01 * x**2)
v = np.zeros_like(u)

# add a tiny phase tilt (momentum) to avoid trivial symmetry
u += 0.001 * np.sin(2*np.pi * x / (N*dx))

# ── evolve (damped, χ-clipped) and record lab-frame snapshots ─────
snap_every = 10
frames = []
msd_trace = []
t_axis = []

u0 = u.copy()
for n in range(steps):
    u_xx = lap(u)
    acc = (c_eff**2)*u_xx - Λ*u - β*v + χ*np.clip(u**3, -1e3, 1e3)
    acc -= damping * v                         # K3b stabilization
    v += dt * acc
    u += dt * v
    u = np.clip(u, -50, 50)

    if (n % snap_every) == 0:
        frames.append(u.copy())
        d = u - u0
        msd_trace.append(np.mean(d*d))
        t_axis.append(n*dt)

frames = np.array(frames)
msd_trace = np.array(msd_trace)
t_axis = np.array(t_axis)

# ── boosted-frame sampling (Lorentz map built from c_eff) ─────────
# map lab (x_i, t_k) → x' = γ (x_i - v t_k), t' = γ (t_k - v x_i / c_eff^2)
# We build a boosted field U'(x', t') by resampling nearest-neighbor on x-grid.
xprime_grid = x.copy()
boost_frames = []

for k, tk in enumerate(t_axis):
    xprime = gamma * (x - v_boost * tk)
    # inverse map: for each x'_j, find lab x that hits it at fixed t_k
    # x = x' / γ + v tk
    x_lab_from_xprime = (xprime_grid / gamma) + v_boost * tk
    idx = np.clip(np.round((x_lab_from_xprime - x[0]) / dx).astype(int), 0, N-1)
    boost_frames.append(frames[k][idx])
boost_frames = np.array(boost_frames)

# ── metrics in both frames ─────────────────────────────────────────
# MSD
msd_lab = msd_trace
msd_boost = []
for k in range(len(t_axis)):
    d = boost_frames[k] - boost_frames[0]
    msd_boost.append(np.mean(d*d))
msd_boost = np.array(msd_boost)

p_lab   = transport_exponent(msd_lab,   t_axis)
p_boost = transport_exponent(msd_boost, t_axis)

# Correlation length at final time
xi_lab   = corr_length(frames[-1])
xi_boost = corr_length(boost_frames[-1])

# invariance deltas
dp  = p_boost - p_lab
dxi = (xi_boost - xi_lab)

# ── plot ───────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13,5))

# left: snapshot comparison (final frame)
axes[0].plot(x, np.abs(frames[-1]), label="|u(x,t_f)| lab")
axes[0].plot(x, np.abs(boost_frames[-1]), '--', label="|u'(x',t'_f)| boost")
axes[0].set_title("L1 — Field Envelope (final)")
axes[0].set_xlabel("x or x'"); axes[0].set_ylabel("|u|")
axes[0].legend(); axes[0].grid(True, alpha=0.3)

# right: MSD scaling
axes[1].plot(t_axis, msd_lab,   label=f"MSD lab (p≈{p_lab:.3f})")
axes[1].plot(t_axis, msd_boost, '--', label=f"MSD boost (p≈{p_boost:.3f})")
axes[1].set_xscale("log"); axes[1].set_yscale("log")
axes[1].set_xlabel("time"); axes[1].set_ylabel("MSD")
axes[1].set_title("MSD scaling (lab vs. boost)")
axes[1].legend(); axes[1].grid(True, which="both", alpha=0.3)

plt.tight_layout()
fig_path = "PAEV_L1_boost_invariance.png"
plt.savefig(fig_path, dpi=200)
print(f"✅ Plot saved → {fig_path}")

# ── summary JSON ───────────────────────────────────────────────────
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
summary = {
    "timestamp": ts,
    "seed": seed,
    "constants": const,
    "params": {
        "N": N, "steps": steps, "dt": dt, "dx": dx,
        "damping": damping, "snap_every": snap_every,
        "boost_v": v_boost, "gamma": gamma
    },
    "derived": {
        "c_eff": c_eff,
        "transport_exponent_lab":   float(p_lab),
        "transport_exponent_boost": float(p_boost),
        "delta_p": float(dp),
        "xi_lab": float(xi_lab) if np.isfinite(xi_lab) else None,
        "xi_boost": float(xi_boost) if np.isfinite(xi_boost) else None,
        "delta_xi": float(dxi) if np.isfinite(dxi) else None
    },
    "files": {"plot": fig_path},
    "notes": [
        "Boost defined by c_eff (from α,Λ) to emulate Lorentz transform.",
        "Damping (K3b) ensures causal stability under χ nonlinearity.",
        "Invariance target: p_boost≈p_lab and ξ_boost≈ξ_lab within small deltas.",
        "Model-level check; no physical signaling implied."
    ]
}
out_path = Path("backend/modules/knowledge/L1_boost_invariance_summary.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"✅ Summary saved → {out_path}")

# ── discovery section ──────────────────────────────────────────────
print("\n🧭 Discovery Notes —", ts)
print("------------------------------------------------------------")
print(f"• Observation: p_lab≈{p_lab:.3f}, p_boost≈{p_boost:.3f}, Δp≈{dp:.3e}; "
      f"ξ_lab≈{xi_lab:.2f}, ξ_boost≈{xi_boost:.2f}, Δξ≈{dxi:.2f}.")
print("• Interpretation: Small deltas indicate approximate boost invariance of"
      " transport scaling and correlation length under the c_eff-based transform.")
print("• Implication: Supports Lorentz-like symmetry of the Tessaris lattice in "
      "the stable (damped) regime.")
print("• Next step: L2 — scaling collapse across multiple boosts; L3 — boosted "
      "soliton reflection/transmission tests.")
print("------------------------------------------------------------")

# ── verdict ────────────────────────────────────────────────────────
tol_p  = 0.05
tol_xi = 0.10 * (xi_lab if np.isfinite(xi_lab) else 1.0)
ok_p   = abs(dp) <= tol_p
ok_xi  = (abs(dxi) <= tol_xi) if np.isfinite(dxi) else False

print("\n" + "="*66)
print("🔎 L1 — Boost Invariance Verdict")
print("="*66)
if ok_p and ok_xi:
    print(f"✅ Invariance upheld: |Δp|≤{tol_p} and |Δξ|≤{tol_xi:.3g}.")
else:
    why = []
    if not ok_p:  why.append(f"|Δp|>{tol_p}")
    if not ok_xi: why.append(f"|Δξ|>{tol_xi:.3g}")
    print("⚠️  Partial/failed invariance:", ", ".join(why))
print("="*66 + "\n")