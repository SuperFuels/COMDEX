import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==========================================================
# F4 - Vacuum Energy Renormalization (Stabilized Bounce)
# ==========================================================
# Purpose:
#   Stabilize the F3 instability by introducing a renormalized
#   vacuum term Λ_eff(φ), adaptive damping, and limited feedback.
# ==========================================================

np.random.seed(42)

# --- Simulation parameters ---
dt = 0.002
T = 3000
t = np.arange(T) * dt

# --- Physical constants (baseline from F3, tuned for stability) ---
alpha = 0.7
beta = 0.08            # reduced quartic coupling
Lambda_base = 0.0035
kappa = 0.065
omega0 = 0.18
xi = 0.015
delta = 0.05
noise = 0.001
w_m = 0.1

# --- New renormalization parameters ---
gamma = 0.85        # vacuum suppression factor
phi_crit = 1.8      # critical scalar amplitude
damp_gain = 0.005   # adaptive damping proportional to energy density
Lambda_dyn_max = 0.02  # limit for dynamic control

# --- Controller (simplified F3) ---
ctrl = dict(kp=0.3, ki=0.005, kd=0.08, soft_floor=-0.015, soft_ceil=0.015)

# --- State variables ---
a = np.zeros(T)
H = np.zeros(T)
phi = np.zeros(T)
phid = np.zeros(T)
rho_tot = np.zeros(T)
rho_phi = np.zeros(T)
rho_m = np.zeros(T)
rho_curv = np.zeros(T)
rho_vac = np.zeros(T)
Lambda_eff = np.zeros(T)

# --- Initial conditions ---
a[0] = 1.0
H[0] = -0.25
phi[0] = 0.4
phid[0] = -0.03
Lambda_eff[0] = Lambda_base

# --- Functions ---
def V(phi):
    return 0.5 * (omega0 ** 2) * phi ** 2 + beta * phi ** 4

def dV(phi):
    return (omega0 ** 2) * phi + 4 * beta * phi ** 3

def renormalized_Lambda(phi):
    """Vacuum suppression for large field amplitudes."""
    return Lambda_base * (1 - gamma * np.tanh((phi / phi_crit) ** 2))

# --- Simulation loop ---
Lambda_dyn = 0.0
e_int = 0.0
E_prev = 0.0
for i in range(1, T):
    # Renormalized vacuum term
    Lambda_eff[i] = renormalized_Lambda(phi[i-1]) + Lambda_dyn
    Lambda_eff[i] = np.clip(Lambda_eff[i], -0.05, 0.05)

    # Energy densities
    rho_m[i] = kappa / (a[i-1] ** (3 * (1 + w_m)))
    rho_phi[i] = 0.5 * (phid[i-1] ** 2) + V(phi[i-1])
    rho_curv[i] = delta / (a[i-1] ** 2)
    rho_vac[i] = Lambda_eff[i]
    rho_tot[i] = rho_m[i] + rho_phi[i] + rho_curv[i] + rho_vac[i]

    # Adaptive damping
    damping = 1 + damp_gain * min(rho_tot[i], 1e4)

    # Friedmann-like update for Hubble parameter
    H[i] = H[i-1] + dt * (-alpha * rho_m[i] + Lambda_eff[i] - xi * H[i-1] * damping)

    # Scale factor
    a[i] = max(1e-6, a[i-1] + a[i-1] * H[i] * dt)

    # Scalar field with adaptive damping
    phidd = -3 * H[i] * phid[i-1] - dV(phi[i-1]) / damping
    phid[i] = phid[i-1] + dt * phidd + np.random.normal(0, noise)
    phi[i] = phi[i-1] + dt * phid[i]

    # Feedback correction (simplified F3)
    E = rho_tot[i]
    e = E - 0.5
    e_int += e * dt
    Lambda_dyn -= ctrl["kp"] * e + ctrl["ki"] * e_int
    Lambda_dyn = np.clip(Lambda_dyn, ctrl["soft_floor"], ctrl["soft_ceil"])

# --- Metrics ---
a_min = float(np.min(a))
a_max = float(np.max(a))
bounce_index = int(np.argmin(a))
energy_min = float(np.min(rho_tot))
energy_max = float(np.max(rho_tot))
mean_coherence = float(np.mean(np.cos(phi)))
coherence_stability = float(np.std(np.cos(phi)))
anti_corr = float(np.corrcoef(rho_tot, -Lambda_eff)[0,1])

# --- Classification ---
if a_min > 0.05 and mean_coherence > 0.65 and energy_max < 500:
    verdict = "✅ Stable Bounce (Renormalized Vacuum)"
elif a_min > 0.02 and mean_coherence > 0.5:
    verdict = "⚠️ Semi-Stable Rebound (partial coherence)"
else:
    verdict = "❌ Collapse (energy runaway)"

# --- Plots ---
plt.figure(figsize=(9, 5))
plt.plot(t, a, label="a(t)")
plt.axvline(t[bounce_index], color="purple", ls="--", label="bounce")
plt.title("F4 - Scale Factor Evolution (Renormalized Vacuum)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F4_ScaleFactorEvolution.png")

plt.figure(figsize=(9, 5))
plt.plot(t, rho_tot, label="ρ_total", lw=1.3)
plt.plot(t, rho_phi, label="ρ_φ", alpha=0.6)
plt.plot(t, rho_vac, "--", label="Λ_eff(t)", alpha=0.7)
plt.yscale("log")
plt.title("F4 - Energy Density and Renormalized Vacuum")
plt.xlabel("time"); plt.ylabel("Energy (arb. units, log)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F4_EnergyDecomposition.png")

plt.figure(figsize=(9, 5))
plt.plot(t, np.cos(phi), lw=1.0, label="cos(φ)")
plt.title("F4 - Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F4_PhaseCoherence.png")

# --- Save Results ---
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
        "gamma": gamma,
        "phi_crit": phi_crit,
        "damp_gain": damp_gain
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
        "scale_plot": "FAEV_F4_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F4_EnergyDecomposition.png",
        "phase_plot": "FAEV_F4_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F4_vacuum_renormalization.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F4 - Vacuum Energy Renormalization (Stabilized Bounce) ===")
print(f"a_min={a_min:.4f} | mean_coherence={mean_coherence:.3f} | anti-corr(Λ,E)={anti_corr:.2f}")
print(f"-> {verdict}")
print("✅ Results saved -> backend/modules/knowledge/F4_vacuum_renormalization.json")