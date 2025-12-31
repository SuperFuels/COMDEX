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
# Files out:
#   FAEV_F3_ScaleFactorEvolution.png
#   FAEV_F3_EnergyDecomposition.png
#   FAEV_F3_PhaseCoherence.png
#   backend/modules/knowledge/F3_vacuum_cancellation.json
# ==========================================================

np.random.seed(7)

# --- sim params ---
dt = 0.002
T  = 2800     # steps (same horizon as F2)
t  = np.arange(T)*dt

# --- model constants (kept close to F2 for comparability) ---
alpha   = 0.70   # coupling of scalar to expansion
beta    = 0.15   # nonlinear scattering in scalar potential
kappa   = 0.065  # matter/radiation mix strength
omega0  = 0.20   # scalar harmonic freq
xi      = 0.015  # Hubble-friction coupling on scalar
delta   = 0.05   # mild curvature term
noise   = 0.0012 # small stochasticity

# static baselines
Lambda_base = 0.0035          # static vacuum baseline
w_m         = 0.10            # effective EOS for the matter mix (between dust/rad)
curv_sign   = +1.0            # closed-like

# --- controller for Λ cancellation (new in F3) ---
# It looks at total energy surge & "distance-to-bounce" proxy and injects anti-pressure.
ctrl = dict(
    kp = 0.45,               # proportional on energy surge
    ki = 0.008,              # integral (slow, anti-windup bounded)
    kd = 0.10,               # derivative (energy slope), LP-filtered
    i_min = -0.02, i_max = 0.02,
    d_alpha = 0.15,          # LPF for derivative
    boost_near_bounce = 0.7, # extra gain when H~0 & a near min
    soft_floor = -0.030,     # Λ_dyn lower bound (prevents runaway)
    soft_ceil  = +0.030      # Λ_dyn upper bound
)

# --- state arrays ---
a   = np.zeros(T)
H   = np.zeros(T)
phi = np.zeros(T)
phid= np.zeros(T)
Rcoh= np.zeros(T)  # phase coherence cos(phi)
rho_m = np.zeros(T)
rho_phi = np.zeros(T)
rho_curv= np.zeros(T)
rho_vac = np.zeros(T)
rho_tot = np.zeros(T)
Lambda_dyn = np.zeros(T)

# --- initial conditions (same spirit as F2) ---
a[0] = 1.0
H[0] = -0.30     # contracting
phi[0] = 0.35
phid[0] = -0.02

# --- controller state ---
e_int = 0.0
e_der = 0.0
E_prev = 0.0

def scalar_potential(phi):
    # V = 0.5*omega0^2*phi^2 + beta * phi^4
    return 0.5*(omega0**2)*(phi**2) + beta*(phi**4)

def total_energy(a_now, phi_now, phid_now, Lam_now):
    # matter/radiation effective mix
    rho_m_now = kappa / (a_now**(3*(1.0+w_m)))
    # curvature
    rho_k_now = curv_sign * delta / (a_now**2)
    # scalar field energy
    rho_phi_now = 0.5*(phid_now**2) + scalar_potential(phi_now)
    # vacuum
    rho_vac_now = Lam_now
    # total
    return rho_m_now, rho_k_now, rho_phi_now, rho_vac_now, (rho_m_now + rho_k_now + rho_phi_now + rho_vac_now)

def hubble_from_energy(rho_total):
    # Simple "Friedmann-like" surrogate: H^2 ~ alpha * rho_total
    # (alpha plays the role of 8πG/3 up to units)
    Hsq = np.maximum(1e-10, alpha * rho_total)
    return np.sign(H[0]) * np.sqrt(Hsq)  # sign carried from dynamics (updated below)

def near_bounce_weight(a_hist, H_now):
    """Heuristic weight: high near turning points (small |H| and local a minimum)."""
    wH = np.exp(-20.0*(np.abs(H_now)))
    if len(a_hist) < 5:
        return wH
    # curvature of a(t): positive when a is at a trough
    curv = a_hist[-1] - 2.0*a_hist[-2] + a_hist[-3]
    wC = 1.0 / (1.0 + np.exp(-250.0*curv))  # ~1 near convex trough
    return np.clip(0.5*wH + 0.5*wC, 0.0, 1.0)

# --- simulate ---
for i in range(1, T):
    # 1) energies with current Λ = base + dynamic
    Lam_now = Lambda_base + Lambda_dyn[i-1]
    rm, rk, rphi, rvac, rtot = total_energy(max(1e-3, a[i-1]), phi[i-1], phid[i-1], Lam_now)

    rho_m[i-1], rho_curv[i-1], rho_phi[i-1], rho_vac[i-1], rho_tot[i-1] = rm, rk, rphi, rvac, rtot

    # 2) update H (carry sign by dynamics): dH from pressure-like surrogate
    #    Use simple relaxation toward sqrt law with damping by sign reversals.
    H_target = np.sqrt(max(1e-10, alpha*rtot))
    # choose sign from previous step; allow flips when d(a)/dt crosses 0
    sign_prev = np.sign(H[i-1]) if H[i-1] != 0 else -1.0
    H_goal = sign_prev * H_target
    H[i] = 0.92*H[i-1] + 0.08*H_goal  # gently track the target

    # 3) evolve a(t)
    a[i] = max(1e-6, a[i-1] + dt * a[i-1] * H[i])

    # 4) evolve scalar field with Hubble friction and mild noise
    #    phidd + 3H phid + dV/dphi = 0
    dV = (omega0**2)*phi[i-1] + 4.0*beta*(phi[i-1]**3)
    phidd = -3.0*xi*H[i]*phid[i-1] - dV
    phid[i] = phid[i-1] + dt*phidd + np.random.normal(0, noise*0.2)
    phi[i]  = phi[i-1]  + dt*phid[i]
    Rcoh[i] = np.cos(phi[i])

    # 5) Adaptive Λ_dyn control - cancel surges near bounce
    # Error signal: excess total energy above a soft baseline
    E = rtot
    e = E - 0.20   # soft bias so we don't kill expansion energy far from bounce

    # derivative (LPF)
    e_der = (1.0-ctrl["d_alpha"])*e_der + ctrl["d_alpha"]*(e - E_prev)
    E_prev = e

    # integral with anti-windup
    e_int = np.clip(e_int + e*dt, ctrl["i_min"], ctrl["i_max"])

    # near-bounce gain boost
    nb = near_bounce_weight(a[:i], H[i])
    u = (ctrl["kp"]*e + ctrl["ki"]*e_int + ctrl["kd"]*e_der) * (1.0 + ctrl["boost_near_bounce"]*nb)

    # clamp Λ_dyn
    Lambda_dyn[i] = np.clip(Lambda_dyn[i-1] - u*dt, ctrl["soft_floor"], ctrl["soft_ceil"])  # minus sign -> counter-pressure

# final energy slice
Lam_now = Lambda_base + Lambda_dyn[-1]
rm, rk, rphi, rvac, rtot = total_energy(max(1e-3, a[-1]), phi[-1], phid[-1], Lam_now)
rho_m[-1], rho_curv[-1], rho_phi[-1], rho_vac[-1], rho_tot[-1] = rm, rk, rphi, rvac, rtot

# --- metrics ---
a_min = float(np.min(a))
a_max = float(np.max(a))
# detect bounce index (first local min of a after strong contraction)
bounce_idx = int(np.argmin(a))
energy_min = float(np.min(rho_tot))
energy_max = float(np.max(rho_tot))
mean_coh = float(np.mean(Rcoh[max(0, bounce_idx-200): min(T, bounce_idx+400)]))
coh_stab = float(np.std(Rcoh[max(0, bounce_idx-200): min(T, bounce_idx+400)]))

# cancellation efficiency: how much Λ_dyn moves opposite to total energy near bounce
win = slice(max(0, bounce_idx-200), min(T, bounce_idx+200))
anti_corr = float(np.corrcoef(rho_tot[win], -(Lambda_dyn[win]))[0,1])

# classify
if (a_min < 0.13 and mean_coh > 0.72 and anti_corr > 0.6 and energy_max < 0.5*max(1.0, np.percentile(rho_tot, 99))):
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
plt.savefig("FAEV_F3_ScaleFactorEvolution.png")

# 2) Energy decomposition
plt.figure(figsize=(10.0, 4.8))
plt.plot(t, rho_tot, label="ρ_total", lw=1.5)
plt.plot(t, rho_m,   label="ρ_m", alpha=0.6)
plt.plot(t, rho_phi, label="ρ_φ", alpha=0.6)
plt.plot(t, rho_curv,label="ρ_curv", alpha=0.6)
plt.plot(t, Lambda_base + Lambda_dyn, "--", color="gray", label="Λ(t)")
plt.yscale("log")
plt.title("F3 - Energy Density and Dynamic Vacuum Λ(t)")
plt.xlabel("time"); plt.ylabel("Energy (arb. units, log)")
plt.legend(ncol=3)
plt.tight_layout()
plt.savefig("FAEV_F3_EnergyDecomposition.png")

# 3) Phase coherence
plt.figure(figsize=(9.5, 4.4))
plt.plot(t, np.clip(Rcoh, -1, 1), label="cos(φ)")
plt.axvline(t[bounce_idx], color="purple", ls="--", alpha=0.7)
plt.title("F3 - Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_F3_PhaseCoherence.png")

# --- save JSON ---
result = {
    "eta": 0.001,
    "dt": dt,
    "T": T,
    "constants": {
        "alpha": alpha, "beta": beta, "Lambda_base": Lambda_base, "kappa": kappa,
        "omega0": omega0, "xi": xi, "delta": delta, "noise": noise, "w_m": w_m
    },
    "controller": ctrl,
    "metrics": {
        "a_min": a_min,
        "a_max": a_max,
        "bounce_index": int(bounce_idx),
        "energy_min": float(energy_min),
        "energy_max": float(energy_max),
        "mean_coherence": mean_coh,
        "coherence_stability": coh_stab,
        "anti_correlation_Lambda_vs_E": anti_corr
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
print(f"a_min={a_min:.4f} | mean_coherence={mean_coh:.3f} | anti-corr(Λ,E)={anti_corr:.2f}")
print(f"-> {verdict}")
print("✅ Results saved -> backend/modules/knowledge/F3_vacuum_cancellation.json")