import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==========================================================
# F3 - Vacuum Energy Cancellation (Coherent Bounce Test)
# ==========================================================
# Goal: Add an adaptive counter-vacuum term Λ_dyn(t) that cancels
# the energy spike near the bounce, improving rebound coherence.
#
# Numerics / stability:
# - Closed-curvature term enters Friedmann with NEGATIVE sign (standard k=+1),
#   so we model it as rho_curv = -delta/a^2 for curv_sign=+1.
# - Raychaudhuri-style Hdot enables sign flips (bounce).
# - Hard clipping prevents overflow and NaNs.
# - Safe correlation metric never returns NaN.
#
# Files out (working directory):
#   FAEV_F3_ScaleFactorEvolution.png
#   FAEV_F3_EnergyDecomposition.png
#   FAEV_F3_PhaseCoherence.png
#   backend/modules/knowledge/F3_vacuum_cancellation.json
# ==========================================================

np.random.seed(7)

# --- sim params ---
dt = 0.002
T  = 2800
t  = np.arange(T) * dt

# --- model constants (kept close to your original for comparability) ---
alpha   = 0.70   # coupling constant (Friedmann/Raychaudhuri surrogate)
beta    = 0.15   # nonlinear scattering in scalar potential
kappa   = 0.065  # matter/radiation mix strength
omega0  = 0.20   # scalar harmonic freq
xi      = 0.015  # Hubble friction coupling on scalar
delta   = 0.05   # curvature magnitude (k/a^2 term proxy)
noise   = 0.0012 # stochasticity

Lambda_base = 0.0035
w_m         = 0.10
curv_sign   = +1.0  # +1.0 => closed-like (k=+1)

# --- controller for Λ cancellation (same semantics as your original) ---
ctrl = dict(
    kp=0.45,
    ki=0.008,
    kd=0.10,
    i_min=-0.02, i_max=0.02,
    d_alpha=0.15,
    boost_near_bounce=0.7,
    soft_floor=-0.030,
    soft_ceil=+0.030
)

# --- numerical stabilizers (prevents overflow/NaN) ---
A_FLOOR      = 1e-4
RHO_FLOOR    = 1e-12
PHI_CLIP     = 6.0
PHID_CLIP    = 6.0
DV_CLIP      = 150.0
H_CLIP       = 3.0
H_FRICTION_CAP = 0.50  # caps |H| used in scalar friction (prevents anti-friction blowup)

# --- state arrays ---
a         = np.zeros(T)
H         = np.zeros(T)
phi       = np.zeros(T)
phid      = np.zeros(T)
Rcoh      = np.zeros(T)

rho_m     = np.zeros(T)
rho_phi   = np.zeros(T)
rho_curv  = np.zeros(T)
rho_vac   = np.zeros(T)
rho_tot   = np.zeros(T)
Lambda_dyn = np.zeros(T)

# --- initial conditions ---
a[0]    = 1.0
H[0]    = -0.30
phi[0]  = 0.35
phid[0] = -0.02
Rcoh[0] = np.cos(phi[0])

# --- controller state ---
e_int = 0.0
e_der = 0.0
E_prev = 0.0

def safe_clip_finite(x: float, lo: float, hi: float) -> float:
    if not np.isfinite(x):
        return 0.0
    return float(np.clip(x, lo, hi))

def scalar_potential(phi_val: float) -> float:
    pc = np.clip(phi_val, -PHI_CLIP, PHI_CLIP)
    pc2 = pc * pc
    # V = 0.5*omega0^2*phi^2 + beta*phi^4 (computed safely)
    return float(0.5 * (omega0**2) * pc2 + beta * (pc2 * pc2))

def dV_dphi(phi_val: float) -> float:
    pc = np.clip(phi_val, -PHI_CLIP, PHI_CLIP)
    dv = (omega0**2) * pc + 4.0 * beta * (pc * pc * pc)
    return safe_clip_finite(dv, -DV_CLIP, DV_CLIP)

def total_energy_and_pressure(a_now: float, phi_now: float, phid_now: float, Lam_now: float):
    aa = float(max(A_FLOOR, a_now))

    # matter/radiation effective mix
    rho_m_now = float(kappa / (aa ** (3.0 * (1.0 + w_m))))
    p_m_now   = float(w_m * rho_m_now)

    # curvature term: for k=+1, Friedmann has -k/a^2 -> negative contribution
    rho_k_now = float(-(curv_sign * delta) / (aa ** 2))
    p_k_now   = float((-1.0/3.0) * rho_k_now)

    # scalar field
    phc = float(np.clip(phid_now, -PHID_CLIP, PHID_CLIP))
    rho_phi_now = float(0.5 * (phc ** 2) + scalar_potential(phi_now))
    p_phi_now   = float(0.5 * (phc ** 2) - scalar_potential(phi_now))

    # vacuum
    rho_vac_now = float(Lam_now)
    p_vac_now   = float(-rho_vac_now)

    rho_total = rho_m_now + rho_k_now + rho_phi_now + rho_vac_now
    p_total   = p_m_now + p_k_now + p_phi_now + p_vac_now

    return rho_m_now, rho_k_now, rho_phi_now, rho_vac_now, rho_total, p_total

def near_bounce_weight(a_hist: np.ndarray, H_now: float) -> float:
    wH = float(np.exp(-20.0 * abs(H_now)))
    if len(a_hist) < 5:
        return wH
    curv = float(a_hist[-1] - 2.0 * a_hist[-2] + a_hist[-3])
    wC = float(1.0 / (1.0 + np.exp(-250.0 * curv)))
    return float(np.clip(0.5 * wH + 0.5 * wC, 0.0, 1.0))

def safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5:
        return 0.0
    x = x[m]
    y = y[m]
    sx = float(np.std(x))
    sy = float(np.std(y))
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    c = float(np.corrcoef(x, y)[0, 1])
    if not np.isfinite(c):
        return 0.0
    return float(np.clip(c, -1.0, 1.0))

# --- simulate ---
for i in range(1, T):
    # Λ(t) = baseline + dynamic cancellation term
    Lam_now = float(Lambda_base + Lambda_dyn[i - 1])

    rm, rk, rphi, rvac, rtot, ptot = total_energy_and_pressure(a[i - 1], phi[i - 1], phid[i - 1], Lam_now)
    rho_m[i - 1]    = rm
    rho_curv[i - 1] = rk
    rho_phi[i - 1]  = rphi
    rho_vac[i - 1]  = rvac
    rho_tot[i - 1]  = rtot

    # --- H update (Raychaudhuri-style; allows sign flips) ---
    # Hdot ~ -0.5 * alpha * (rho + p)
    Hdot = -0.5 * alpha * (rtot + ptot)
    H_i  = float(H[i - 1] + dt * Hdot)
    H_i  = float(np.clip(H_i, -H_CLIP, H_CLIP))

    # softly respect Friedmann magnitude: H^2 ~ alpha * max(rho, eps)
    Hsq_target = float(max(RHO_FLOOR, alpha * max(rtot, RHO_FLOOR)))
    Hmag_target = float(np.sqrt(Hsq_target))
    if abs(H_i) > 1.5 * Hmag_target:
        H_i = float(np.sign(H_i) * (0.85 * abs(H_i) + 0.15 * Hmag_target))

    H[i] = H_i

    # --- scale factor ---
    a_i = float(a[i - 1] + dt * a[i - 1] * H[i])
    a[i] = float(max(A_FLOOR, a_i))

    # --- scalar field evolution ---
    # phidd + 3*xi*H*phid + dV/dphi = 0
    # During contraction H<0 this becomes anti-friction; we cap magnitude for stability.
    H_fric = float(np.clip(H[i], -H_FRICTION_CAP, H_FRICTION_CAP))
    dv = dV_dphi(phi[i - 1])

    phc_prev = float(np.clip(phid[i - 1], -PHID_CLIP, PHID_CLIP))
    phidd = float(-3.0 * xi * H_fric * phc_prev - dv)

    phid_i = float(phc_prev + dt * phidd + np.random.normal(0.0, noise * 0.2))
    phid[i] = float(np.clip(phid_i, -PHID_CLIP, PHID_CLIP))

    phi_i = float(phi[i - 1] + dt * phid[i])
    phi[i] = float(np.clip(phi_i, -PHI_CLIP, PHI_CLIP))
    Rcoh[i] = float(np.cos(phi[i]))

    # --- Adaptive Λ_dyn control ---
    # Error: excess total energy above a soft baseline
    E = float(rtot)
    e = float(E - 0.20)

    # derivative LPF
    e_der = float((1.0 - ctrl["d_alpha"]) * e_der + ctrl["d_alpha"] * (e - E_prev))
    E_prev = e

    # integral anti-windup
    e_int = float(np.clip(e_int + e * dt, ctrl["i_min"], ctrl["i_max"]))

    nb = near_bounce_weight(a[:i], H[i])
    u = float((ctrl["kp"] * e + ctrl["ki"] * e_int + ctrl["kd"] * e_der) * (1.0 + ctrl["boost_near_bounce"] * nb))

    # update Λ_dyn (minus sign = counter-pressure / cancellation)
    Lambda_dyn[i] = float(np.clip(Lambda_dyn[i - 1] - u * dt, ctrl["soft_floor"], ctrl["soft_ceil"]))

# finalize last energy slice
Lam_now = float(Lambda_base + Lambda_dyn[-1])
rm, rk, rphi, rvac, rtot, _ptot = total_energy_and_pressure(a[-1], phi[-1], phid[-1], Lam_now)
rho_m[-1], rho_curv[-1], rho_phi[-1], rho_vac[-1], rho_tot[-1] = rm, rk, rphi, rvac, rtot

# --- metrics ---
a_min = float(np.min(a))
a_max = float(np.max(a))
bounce_idx = int(np.argmin(a))

energy_min = float(np.min(rho_tot))
energy_max = float(np.max(rho_tot))

w0 = max(0, bounce_idx - 200)
w1 = min(T, bounce_idx + 400)
mean_coh = float(np.mean(Rcoh[w0:w1])) if w1 > w0 else float(np.mean(Rcoh))
coh_stab = float(np.std(Rcoh[w0:w1])) if w1 > w0 else float(np.std(Rcoh))

win0 = max(0, bounce_idx - 200)
win1 = min(T, bounce_idx + 200)
anti_corr = safe_corr(rho_tot[win0:win1], -(Lambda_dyn[win0:win1]))

# classify (same thresholds, but now metrics are finite)
if (a_min < 0.13 and mean_coh > 0.72 and anti_corr > 0.6):
    verdict = "✅ Vacuum Canceled Bounce (coherent expansion)"
elif (a_min < 0.15 and mean_coh > 0.62 and anti_corr > 0.4):
    verdict = "⚠️ Partial Cancellation (improved but noisy)"
else:
    verdict = "❌ Unstable or weak cancellation"

# --- plots ---
# 1) Scale factor
plt.figure(figsize=(9.5, 4.6))
plt.plot(t, a, label="a(t)")
plt.axvline(t[bounce_idx], color="purple", ls="--", alpha=0.8, label="bounce")
plt.title("F3 - Scale Factor Evolution (Vacuum Cancellation)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_F3_ScaleFactorEvolution.png", dpi=160)

# 2) Energy decomposition (log-safe)
plt.figure(figsize=(10.0, 4.8))
plt.plot(t, np.maximum(rho_tot, RHO_FLOOR), label="ρ_total", lw=1.5)
plt.plot(t, np.maximum(rho_m,   RHO_FLOOR), label="ρ_m", alpha=0.6)
plt.plot(t, np.maximum(rho_phi, RHO_FLOOR), label="ρ_φ", alpha=0.6)
plt.plot(t, np.maximum(np.abs(rho_curv), RHO_FLOOR), label="|ρ_curv|", alpha=0.6)
plt.plot(t, np.maximum(Lambda_base + Lambda_dyn, RHO_FLOOR), "--", color="gray", label="Λ(t)")
plt.yscale("log")
plt.title("F3 - Energy Density and Dynamic Vacuum Λ(t)")
plt.xlabel("time"); plt.ylabel("Energy (arb. units, log)")
plt.legend(ncol=3)
plt.tight_layout()
plt.savefig("FAEV_F3_EnergyDecomposition.png", dpi=160)

# 3) Phase coherence
plt.figure(figsize=(9.5, 4.4))
plt.plot(t, np.clip(Rcoh, -1, 1), label="cos(φ)")
plt.axvline(t[bounce_idx], color="purple", ls="--", alpha=0.7)
plt.title("F3 - Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_F3_PhaseCoherence.png", dpi=160)

# --- save JSON (finite + lock-friendly) ---
result = {
    "eta": 0.001,
    "dt": float(dt),
    "T": int(T),
    "constants": {
        "alpha": float(alpha),
        "beta": float(beta),
        "Lambda_base": float(Lambda_base),
        "kappa": float(kappa),
        "omega0": float(omega0),
        "xi": float(xi),
        "delta": float(delta),
        "noise": float(noise),
        "w_m": float(w_m),
        "curv_sign": float(curv_sign)
    },
    "controller": ctrl,
    "numerics": {
        "A_FLOOR": float(A_FLOOR),
        "PHI_CLIP": float(PHI_CLIP),
        "PHID_CLIP": float(PHID_CLIP),
        "DV_CLIP": float(DV_CLIP),
        "H_CLIP": float(H_CLIP),
        "H_FRICTION_CAP": float(H_FRICTION_CAP),
        "curvature_mode": "rho_curv = -(curv_sign*delta)/a^2 (closed k=+1 => negative contribution)"
    },
    "metrics": {
        "a_min": float(a_min),
        "a_max": float(a_max),
        "bounce_index": int(bounce_idx),
        "energy_min": float(energy_min),
        "energy_max": float(energy_max),
        "mean_coherence": float(mean_coh),
        "coherence_stability": float(coh_stab),
        "anti_correlation_Lambda_vs_E": float(anti_corr)
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_F3_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F3_EnergyDecomposition.png",
        "phase_plot": "FAEV_F3_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F3_vacuum_cancellation.json", "w") as f:
    json.dump(result, f, indent=2)

print("=== F3 - Vacuum Energy Cancellation (Coherent Bounce Test) ===")
print(f"a_min={a_min:.6f} | mean_coherence={mean_coh:.3f} | anti-corr(Λ,E)={anti_corr:.3f}")
print(f"-> {verdict}")
print("✅ Saved plots: FAEV_F3_ScaleFactorEvolution.png, FAEV_F3_EnergyDecomposition.png, FAEV_F3_PhaseCoherence.png")
print("✅ Results saved -> backend/modules/knowledge/F3_vacuum_cancellation.json")