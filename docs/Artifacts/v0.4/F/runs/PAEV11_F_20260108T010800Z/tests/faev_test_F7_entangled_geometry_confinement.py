# ==========================================================
# F7 - Entangled Geometry Confinement (Nonlocal Quantum Memory)
# HARDENED: clamps + finite guards + plot-safe + always writes JSON
# ==========================================================

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ---------------- helpers ----------------
def _finite(x, default=0.0):
    try:
        x = float(x)
    except Exception:
        return float(default)
    return x if np.isfinite(x) else float(default)

def _corr(x, y, default=0.0):
    try:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if x.size < 3 or y.size < 3:
            return float(default)
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 3:
            return float(default)
        c = np.corrcoef(x[m], y[m])[0, 1]
        return float(c) if np.isfinite(c) else float(default)
    except Exception:
        return float(default)

def _clip_finite(arr, lo, hi):
    arr = np.asarray(arr, dtype=float)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    return np.clip(arr, lo, hi)

# ---------------- params ----------------
np.random.seed(42)

dt = 0.002
T = 4000
t = np.arange(T) * dt

alpha = 0.7
beta = 0.08
Lambda_base = 0.0035
kappa = 0.065
omega0 = 0.18
xi = 0.015
delta = 0.05
noise = 0.001
phi_clip = 8.0          # tighter clamp than before
w_m = 0.1

eta_Q = 0.015
zeta_Q = 0.004
xi_Q = 0.0008

eta_E = 0.02
tau_E = 0.12
lambda_E = 18.0

# numeric safety clamps
RHO_CLIP = 1e6          # max allowed magnitude for densities (prevents inf)
D_E_CLIP = 1e6          # max allowed magnitude for dE
LAMBDA_CLIP_LO = -0.01
LAMBDA_CLIP_HI = 0.02

# ---------------- state ----------------
a = np.zeros(T)
H = np.zeros(T)
phi = np.zeros(T)
phid = np.zeros(T)

rho_tot = np.zeros(T)
rho_phi = np.zeros(T)
rho_m = np.zeros(T)
rho_curv = np.zeros(T)

Lambda_eff = np.zeros(T)
Q_mem = np.zeros(T)

a[0] = 1.0
H[0] = -0.25
phi[0] = 0.35
phid[0] = -0.02
Lambda_eff[0] = Lambda_base

# ---------------- potential ----------------
def V(phi_val: float) -> float:
    # clamp phi *inside* energy to prevent polynomial overflow
    p = float(np.clip(phi_val, -phi_clip, phi_clip))
    # bounded quartic
    v = 0.5 * (omega0 ** 2) * p * p + beta * (p ** 4) / (1.0 + p * p)
    return float(np.clip(v, -RHO_CLIP, RHO_CLIP))

def dV(phi_val: float) -> float:
    p = float(np.clip(phi_val, -phi_clip, phi_clip))
    denom = 1.0 + p * p
    dv = (omega0 ** 2) * p + (4.0 * beta * p ** 3 / denom) - (2.0 * beta * p ** 5 / (denom ** 2))
    return float(np.clip(dv, -RHO_CLIP, RHO_CLIP))

# ---------------- simulate ----------------
window = int(tau_E / dt) if tau_E > 0 else 0

for i in range(1, T):
    a_prev = max(1e-6, a[i - 1])

    # matter density
    rho_m_i = kappa / (a_prev ** (3.0 * (1.0 + w_m)))
    rho_m_i = float(np.clip(rho_m_i, 0.0, RHO_CLIP))
    rho_m[i] = rho_m_i

    # scalar energy
    phi_prev = float(np.clip(phi[i - 1], -phi_clip, phi_clip))
    rho_phi_i = 0.5 * (phid[i - 1] ** 2) + V(phi_prev)
    rho_phi_i = float(np.clip(rho_phi_i, 0.0, RHO_CLIP))
    rho_phi[i] = rho_phi_i

    # curvature term
    rho_curv_i = delta / (a_prev ** 2 + 1e-6)
    rho_curv_i = float(np.clip(rho_curv_i, 0.0, RHO_CLIP))
    rho_curv[i] = rho_curv_i

    # total
    rt = rho_m_i + rho_phi_i + rho_curv_i + float(Lambda_eff[i - 1])
    rt = float(np.clip(rt, -RHO_CLIP, RHO_CLIP))
    rho_tot[i] = rt

    # dE (guard non-finite)
    if i > 1:
        dE = (rho_tot[i] - rho_tot[i - 1]) / dt
    else:
        dE = 0.0
    dE = _finite(dE, 0.0)
    dE = float(np.clip(dE, -D_E_CLIP, D_E_CLIP))

    # Λ feedback
    Lam = Lambda_eff[i - 1] - zeta_Q * dE + np.random.normal(0.0, xi_Q)
    Lam = _finite(Lam, Lambda_eff[i - 1])
    Lam = float(np.clip(Lam, LAMBDA_CLIP_LO, LAMBDA_CLIP_HI))
    Lambda_eff[i] = Lam

    # nonlocal memory kernel (based on H history)
    if window >= 3 and i > window:
        H_hist = H[i - window:i]
        dH_hist = np.diff(H_hist) / dt
        dH_hist = _clip_finite(dH_hist, -D_E_CLIP, D_E_CLIP)
        weights = np.exp(-lambda_E * np.linspace(0.0, tau_E, window - 1))
        q = -eta_E * float(np.sum(dH_hist * weights) * dt)
        Q_mem[i] = float(np.clip(_finite(q, 0.0), -RHO_CLIP, RHO_CLIP))
    else:
        Q_mem[i] = 0.0

    # update H and a (guard)
    Hi = H[i - 1] + dt * (-alpha * rho_m_i + Lam - xi * H[i - 1] + Q_mem[i])
    Hi = _finite(Hi, H[i - 1])
    Hi = float(np.clip(Hi, -RHO_CLIP, RHO_CLIP))
    H[i] = Hi

    ai = a_prev + a_prev * Hi * dt
    a[i] = max(1e-6, _finite(ai, a_prev))

    # scalar field evolution
    phidd = -3.0 * Hi * phid[i - 1] - dV(phi_prev)
    phidd = float(np.clip(_finite(phidd, 0.0), -RHO_CLIP, RHO_CLIP))
    phid_i = phid[i - 1] + dt * phidd + np.random.normal(0.0, noise)
    phid_i = float(np.clip(_finite(phid_i, 0.0), -RHO_CLIP, RHO_CLIP))
    phid[i] = phid_i

    phi_i = phi_prev + dt * phid_i
    phi[i] = float(np.clip(_finite(phi_i, phi_prev), -phi_clip, phi_clip))

# ---------------- metrics ----------------
a_min = float(np.min(a))
a_max = float(np.max(a))
bounce_index = int(np.argmin(a))
energy_min = float(np.min(rho_tot))
energy_max = float(np.max(rho_tot))

cos_phi = np.cos(np.clip(phi, -phi_clip, phi_clip))
mean_coherence = _finite(np.mean(cos_phi), 0.0)
coherence_stability = _finite(np.std(cos_phi[-400:]) if T >= 400 else np.std(cos_phi), 1.0)
anti_corr = _corr(rho_tot, -Lambda_eff, 0.0)

if a_min > 0.08 and mean_coherence > 0.6 and coherence_stability < 0.25:
    verdict = "✅ Stable Entangled Bounce (Geometry Confinement Achieved)"
elif a_min > 0.04:
    verdict = "⚠️ Partial rebound (nonlocal damping present)"
else:
    verdict = "❌ Collapse or decoherence"

# ---------------- plots (plot-safe) ----------------
def _safe_plot():
    # scale factor
    plt.figure(figsize=(9, 5))
    plt.plot(t, a, label="a(t)", lw=1.4)
    plt.axvline(t[bounce_index], color="purple", ls="--", alpha=0.7, label="bounce")
    plt.title("F7 - Scale Factor Evolution (Entangled Geometry Confinement)")
    plt.xlabel("time")
    plt.ylabel("a(t)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("FAEV_F7_ScaleFactorEvolution.png", dpi=150)
    plt.close()

    # energy plot: only use log if strictly positive and finite
    plt.figure(figsize=(9, 5))
    rt = np.asarray(rho_tot, dtype=float)
    rp = np.asarray(rho_phi, dtype=float)
    le = np.asarray(Lambda_eff, dtype=float)

    plt.plot(t, rt, label="ρ_total", lw=1.2)
    plt.plot(t, rp, label="ρ_φ", alpha=0.7)
    plt.plot(t, le, "--", label="Λ_eff(t)", alpha=0.8)

    ok_log = np.all(np.isfinite(rt)) and np.all(rt > 0) and np.max(rt) < RHO_CLIP
    if ok_log:
        plt.yscale("log")

    plt.title("F7 - Energy Density and Entangled Vacuum Feedback")
    plt.xlabel("time")
    plt.ylabel("Energy")
    plt.legend()
    plt.tight_layout()
    plt.savefig("FAEV_F7_EnergyDecomposition.png", dpi=150)
    plt.close()

    # coherence
    plt.figure(figsize=(9, 5))
    plt.plot(t, cos_phi, lw=1.0, label="cos(φ)")
    plt.title("F7 - Vacuum-Field Phase Coherence")
    plt.xlabel("time")
    plt.ylabel("cos(φ)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("FAEV_F7_PhaseCoherence.png", dpi=150)
    plt.close()

plot_error = None
try:
    _safe_plot()
except Exception as e:
    plot_error = repr(e)

# ---------------- write JSON ALWAYS ----------------
results = {
    "dt": dt,
    "T": T,
    "constants": {
        "alpha": alpha,
        "beta": beta,
        "Lambda_base": Lambda_base,
        "kappa": kappa,
        "omega0": omega0,
        "xi": xi,
        "delta": delta,
        "noise": noise,
        "phi_clip": phi_clip,
        "w_m": w_m,
        "eta_Q": eta_Q,
        "zeta_Q": zeta_Q,
        "xi_Q": xi_Q,
        "eta_E": eta_E,
        "tau_E": tau_E,
        "lambda_E": lambda_E,
        "RHO_CLIP": RHO_CLIP,
        "D_E_CLIP": D_E_CLIP,
    },
    "metrics": {
        "a_min": a_min,
        "a_max": a_max,
        "bounce_index": bounce_index,
        "energy_min": _finite(energy_min, 0.0),
        "energy_max": _finite(energy_max, 0.0),
        "mean_coherence": mean_coherence,
        "coherence_stability": coherence_stability,
        "anti_corr_Lambda_vs_E": anti_corr,
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_F7_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F7_EnergyDecomposition.png",
        "phase_plot": "FAEV_F7_PhaseCoherence.png",
    },
    "plot_error": plot_error,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/F7_entangled_geometry_confinement.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F7 - Entangled Geometry Confinement (Nonlocal Quantum Memory) ===")
print(f"a_min={a_min:.4f} | mean_coherence={mean_coherence:.3f} | anti-corr(Λ,E)={anti_corr:.2f}")
print(f"-> {verdict}")
if plot_error:
    print(f"⚠️ Plot warning captured: {plot_error}")
print("✅ Results saved -> backend/modules/knowledge/F7_entangled_geometry_confinement.json")
