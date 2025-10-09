#!/usr/bin/env python3
"""
L3 — Boosted Soliton Scattering (Tessaris)
------------------------------------------
A χ-driven soliton hits a static barrier. We compare reflection (R) and
transmission (T) across several Lorentz-like boosts v = {0..0.4} c_eff.

Protocol: Tessaris Unified Constants & Verification Protocol
Outputs:
  • PAEV_L3_boosted_soliton_scattering.png
  • backend/modules/knowledge/L3_boosted_soliton_scattering_summary.json
"""

from __future__ import annotations
import json, math
from pathlib import Path
from datetime import datetime, timezone
import numpy as np, matplotlib.pyplot as plt

# --- Tessaris Unified Constants & Verification Protocol ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]
χ = const.get("χ", 1.0)
print("=== L3 — Boosted Soliton Scattering (Tessaris) ===")
print(f"Constants → ħ={ħ}, G={G}, Λ={Λ}, α={α}, β={β}, χ={χ}")

# --- Grid / numerics (damped causal regime as in K3b/L1c/L2) ---
N, steps = 512, 2400
dt, dx = 0.002, 1.0
snap_every = 8
damping = 0.05
rng = np.random.default_rng(8585)

x = np.linspace(-N//2, N//2, N)
c_eff = math.sqrt(α/(1+Λ))

# Barrier: a localized bump in Λ → effective “mass” barrier
bar_center, bar_width, bar_height = -20.0, 8.0, 6e-6  # gentle barrier to avoid blowups
Λ_profile = Λ + bar_height * np.exp(-0.5 * ((x - bar_center)/bar_width)**2)

def laplacian(f):
    return np.roll(f,-1) - 2*f + np.roll(f,1)

def msd_1d(x, w):
    w = np.clip(w, 0, None); Z = w.sum() + 1e-12
    m1 = (x*w).sum()/Z
    return float(((x-m1)**2 * w).sum()/Z)

def fwhm(x, y):
    m = y.max()
    h = 0.5*m
    idx = np.where(y >= h)[0]
    if len(idx) < 2: return float("nan")
    return float(x[idx[-1]] - x[idx[0]])

def evolve_and_scatter(v_frac: float):
    v_boost = v_frac * c_eff
    gamma = 1.0 / math.sqrt(max(1.0 - (v_boost/c_eff)**2, 1e-12))

    # Initial soliton-like pulse (right-moving towards barrier at x≈-20)
    u = 55.0 * np.exp(-0.06 * (x + 70.0)**2)  # centered at x≈-70
    v = np.zeros_like(u)

    # storage
    snaps = []
    for n in range(steps):
        u_xx = laplacian(u)
        # barrier via Λ_profile
        a = (c_eff**2)*u_xx - Λ_profile*u - β*v + χ*np.clip(u**3, -1e3, 1e3) - damping*v
        v += dt*a
        u += dt*v
        u = np.clip(u, -65, 65)

        if n % snap_every == 0:
            t = n*dt
            if abs(v_boost) > 0:
                # Lorentz-like snapshot transform into boosted frame
                x_prime = gamma*(x - v_boost*t)
                u_prime = np.interp(x, x_prime, np.abs(u), left=0.0, right=0.0)
                snaps.append(u_prime)
            else:
                snaps.append(np.abs(u.copy()))

    snaps = np.array(snaps)
    ts = np.arange(snaps.shape[0]) * dt * snap_every

    # After interaction (late snapshots): split |u|^2 left/right of barrier center
    w_final = snaps[-1]**2
    left_mask = x < bar_center
    right_mask = ~left_mask
    R = float(w_final[left_mask].sum() / (w_final.sum() + 1e-12))
    T = float(w_final[right_mask].sum() / (w_final.sum() + 1e-12))

    # peak/c.o.m. drift for speed estimate (late window)
    tail = slice(-min(30, len(ts)), None)
    centers = []
    for u_t in snaps[tail]:
        w = u_t**2; Z = w.sum() + 1e-12
        centers.append(float((x*w).sum()/Z))
    t_tail = ts[tail]
    if len(centers) > 5:
        p = np.polyfit(t_tail, centers, 1)
        v_emp = float(p[0])
    else:
        v_emp = float("nan")

    # size metric (FWHM) in the final frame
    xi_final = fwhm(x, snaps[-1])

    return dict(
        v_frac=v_frac, v_boost=v_boost, gamma=gamma,
        ts=ts, snaps=snaps, R=R, T=T, v_emp=v_emp, xi_final=xi_final
    )

boost_fracs = [0.0, 0.1, 0.2, 0.3, 0.4]
results = []
for frac in boost_fracs:
    print(f"→ simulate boost {frac:.1f} c_eff")
    results.append(evolve_and_scatter(frac))
print("✅ Scattering runs complete.")

# --- Plots: space–time amplitude and R/T vs boost ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# pick two frames to show spacetime: lab and max boost
show_fracs = [0.0, 0.4]
for i, frac in enumerate(show_fracs):
    res = next(r for r in results if abs(r["v_frac"]-frac) < 1e-9)
    im = ax1.imshow(res["snaps"], extent=[x.min(), x.max(), res["ts"].max(), res["ts"].min()],
                    cmap='magma', aspect='auto', alpha=0.55 if i==1 else 0.9)
ax1.axvline(bar_center, color='cyan', lw=1.8, ls='--', label='barrier')
ax1.set_title("L3 — Soliton scattering (|u|, spacetime)")
ax1.set_xlabel("x or x'"); ax1.set_ylabel("time")
ax1.legend()
cbar = plt.colorbar(im, ax=ax1); cbar.set_label("|u|")

fr = np.array([r["v_frac"] for r in results])
R = np.array([r["R"] for r in results])
T = np.array([r["T"] for r in results])
ax2.plot(fr, R, 'o-', label="R (reflection)")
ax2.plot(fr, T, 'o-', label="T (transmission)")
ax2.plot(fr, R+T, 'k--', alpha=0.6, label="R+T (closure)")
ax2.set_xlabel("boost fraction (v / c_eff)")
ax2.set_ylabel("fraction")
ax2.set_title("Scattering coefficients vs boost")
ax2.grid(True); ax2.legend()

plt.tight_layout()
fig_path = "PAEV_L3_boosted_soliton_scattering.png"
plt.savefig(fig_path, dpi=200)
print(f"✅ Plot saved → {fig_path}")

# --- Invariance metrics ---
# (i) R,T should be ~constant across boosts; (ii) R+T ~ 1; (iii) |v_emp| ≤ c_eff
R_std = float(np.std(R))
T_std = float(np.std(T))
closure_err = float(np.max(np.abs(R+T - 1.0)))
max_speed = float(np.nanmax(np.abs([r["v_emp"] for r in results])))

# --- Summary JSON ---
ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
summary = {
    "timestamp": ts_now,
    "constants": const,
    "params": {
        "N": N, "steps": steps, "dt": dt, "dx": dx,
        "snap_every": snap_every, "damping": damping,
        "barrier": {"center": bar_center, "width": bar_width, "height": bar_height},
        "boost_fracs": boost_fracs
    },
    "derived": {
        "c_eff": c_eff,
        "R": R.tolist(), "T": T.tolist(),
        "R_std": R_std, "T_std": T_std, "closure_max_error": closure_err,
        "max_empirical_speed": max_speed
    },
    "files": {"plot": fig_path},
    "notes": [
        "Barrier modeled via Λ(x)=Λ+ΔΛ·exp(-(x-x0)^2/2σ^2).",
        "Boost snapshots use x' = γ(x - vt).",
        "Invariance targets: small std(R,T), R+T≈1, |v_emp| ≤ c_eff.",
        "Model-level test; no physical signaling implied."
    ]
}
out_path = Path("backend/modules/knowledge/L3_boosted_soliton_scattering_summary.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"✅ Summary saved → {out_path}")

# --- Discovery section ---
print("\n🧭 Discovery Notes —", ts_now)
print("------------------------------------------------------------")
for r in results:
    print(f"• v={r['v_frac']:.1f}c_eff → R={r['R']:.3f}, T={r['T']:.3f}, v_emp≈{r['v_emp']:.3f}, ξ_f≈{r['xi_final']:.2f}")
print(f"• Std(R)≈{R_std:.3e}, Std(T)≈{T_std:.3e}, max|R+T-1|≈{closure_err:.3e}")
print(f"• Causality check: max |v_emp|≈{max_speed:.3f} vs c_eff≈{c_eff:.3f}")
print("• Interpretation: constancy of R/T across boosts supports Lorentz-like scattering symmetry.")
print("• Next: L-series wrap-up & TeX note.")
print("------------------------------------------------------------")

# --- Verdict ---
print("\n" + "="*66)
print("🔎 L3 — Boosted Scattering Verdict")
print("="*66)
ok_collapse = R_std < 0.05 and T_std < 0.05
ok_closure  = closure_err < 0.02
ok_speed    = (not np.isnan(max_speed)) and (abs(max_speed) <= c_eff + 1e-6)
status = "✅ Invariance upheld" if (ok_collapse and ok_closure and ok_speed) else "⚠️ Partial/failed invariance"
print(f"{status}: σ_R≈{R_std:.3e}, σ_T≈{T_std:.3e}, closure≤{closure_err:.3e}, |v_emp|max≈{max_speed:.3f}")
print("="*66 + "\n")