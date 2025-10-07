import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==============================================================
# F7b — Stabilized Entangled Geometry (LQC + Damped Λ feedback)
# ==============================================================

np.random.seed(42)

# --- Parameters ---
dt = 0.002
T = 4000
t = np.arange(T) * dt

# --- Constants ---
alpha = 0.7
beta = 0.08
Lambda_base = 0.0035
kappa = 0.065
omega0 = 0.18
xi = 0.015
delta = 0.05
noise = 0.0008

# --- Loop Quantum Cosmology bounce density ---
rho_c = 1.0  # critical density for bounce

# --- PID feedback on Λ_eff ---
kp, ki, kd = 0.2, 0.005, 0.05
Lambda_rate_max = 0.0005
Lambda_eff = np.zeros(T)
Lambda_eff[0] = Lambda_base
integral_err = 0.0
prev_err = 0.0

# --- Arrays ---
a = np.zeros(T)
H = np.zeros(T)
phi = np.zeros(T)
phid = np.zeros(T)
rho_tot = np.zeros(T)
rho_phi = np.zeros(T)
rho_m = np.zeros(T)
rho_curv = np.zeros(T)

# --- Initial conditions ---
a[0] = 1.0
H[0] = -0.25
phi[0] = 0.35
phid[0] = -0.02

# --- Helper functions ---
def V(phi):
    """Saturating potential prevents runaway growth."""
    return 0.5 * (omega0**2) * phi**2 + beta * phi**4 / (1 + phi**2 / 2.5**2)

def dV(phi):
    """Bounded derivative of potential."""
    d = (omega0**2) * phi + 4 * beta * phi**3 / (1 + phi**2 / 2.5**2)
    d -= 2 * beta * phi**5 / ((2.5**2) * (1 + phi**2 / 2.5**2)**2)
    return np.tanh(d / 5.0) * 5.0  # saturation to limit growth

# --- Simulation loop ---
for i in range(1, T):
    # Energy densities
    rho_m[i] = kappa / (a[i-1] ** (3 * (1 + 0.1)))
    rho_phi[i] = 0.5 * (phid[i-1] ** 2) + V(phi[i-1])
    rho_curv[i] = delta / (a[i-1] ** 2 + 1e-6)
    rho_tot[i] = rho_m[i] + rho_phi[i] + rho_curv[i] + Lambda_eff[i-1]
    rho_tot[i] = np.clip(rho_tot[i], 0, 1.5 * rho_c)  # avoid runaway

    # --- LQC correction: modifies H² evolution ---
    H_sq = rho_tot[i] * (1 - rho_tot[i] / rho_c)
    H[i] = np.sign(H[i-1]) * np.sqrt(abs(H_sq)) if H_sq >= 0 else 0.0

    # --- PID control for Λ_eff (smoothly damp energy drift) ---
    err = (rho_c / 2) - rho_tot[i]
    integral_err += err * dt
    d_err = (err - prev_err) / dt if i > 1 else 0.0
    dΛ = kp * err + ki * integral_err + kd * d_err
    dΛ = np.clip(dΛ, -Lambda_rate_max, Lambda_rate_max)
    Lambda_eff[i] = np.clip(Lambda_eff[i-1] + dΛ, -0.01, 0.02)
    prev_err = err

    # --- Update scale factor ---
    a[i] = max(1e-6, a[i-1] + a[i-1] * H[i] * dt)

    # --- Scalar field evolution ---
    phidd = -3 * H[i] * phid[i-1] - dV(phi[i-1])
    phid[i] = phid[i-1] + dt * phidd + np.random.normal(0, noise)
    phi[i] = phi[i-1] + dt * phid[i]
    phi[i] = np.clip(phi[i], -6.0, 6.0)

# --- Metrics ---
a_min = float(np.min(a))
a_max = float(np.max(a))
bounce_index = int(np.argmin(a))
energy_min = float(np.min(rho_tot))
energy_max = float(np.max(rho_tot))
mean_coherence = float(np.mean(np.cos(phi)))
coherence_stability = float(np.std(np.cos(phi)))
anti_corr = float(np.corrcoef(rho_tot, -Lambda_eff)[0, 1])

# --- Classification ---
if a_min > 0.05 and mean_coherence > 0.6:
    verdict = "✅ Stable Bounce Achieved (LQC-regulated)"
elif a_min > 0.02:
    verdict = "⚠️ Soft Bounce / Partial rebound"
else:
    verdict = "❌ Collapse or decoherence"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, a, label="a(t)")
plt.axvline(t[bounce_index], color="purple", ls="--", label="bounce")
plt.title("F7b — Scale Factor Evolution (Stabilized LQC Bounce)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7b_ScaleFactorEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(t, rho_tot, label="ρ_total", lw=1.3)
plt.plot(t, rho_phi, label="ρ_φ", alpha=0.6)
plt.plot(t, Lambda_eff, "--", label="Λ_eff(t)", alpha=0.7)
plt.yscale("log")
plt.title("F7b — Energy Density and Damped Vacuum Feedback")
plt.xlabel("time"); plt.ylabel("Energy (log)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7b_EnergyDecomposition.png")

plt.figure(figsize=(9,5))
plt.plot(t, np.cos(phi), lw=1.0, label="cos(φ)")
plt.title("F7b — Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7b_PhaseCoherence.png")

# --- Save results ---
results = {
    "eta": 0.001,
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
        "rho_c": rho_c,
        "kp": kp,
        "ki": ki,
        "kd": kd
    },
    "metrics": {
        "a_min": a_min,
        "a_max": a_max,
        "bounce_index": bounce_index,
        "energy_min": energy_min,
        "energy_max": energy_max,
        "mean_coherence": mean_coherence,
        "coherence_stability": coherence_stability,
        "anti_corr_Lambda_vs_E": anti_corr
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_F7b_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F7b_EnergyDecomposition.png",
        "phase_plot": "FAEV_F7b_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F7b_stabilized_bounce.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F7b — Stabilized Entangled Geometry (LQC + Damped Λ feedback) ===")
print(f"a_min={a_min:.4f} | mean_coherence={mean_coherence:.3f} | anti-corr(Λ,E)={anti_corr:.2f}")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/F7b_stabilized_bounce.json")