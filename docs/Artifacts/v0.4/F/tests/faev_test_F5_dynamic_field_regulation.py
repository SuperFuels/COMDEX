import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==========================================================
# F5 - Dynamic Field Regulation (Stabilized Energy Bounce)
# ==========================================================
# Purpose:
#   Prevent runaway energy growth seen in F4 by introducing
#   - soft-saturation scalar potential
#   - energy-derivative vacuum feedback
#   - energy-weighted damping
# ==========================================================

np.random.seed(42)

# --- Simulation parameters ---
dt = 0.002
T = 3200
t = np.arange(T) * dt

# --- Physical constants (stabilized regime) ---
alpha = 0.7
beta = 0.08
Lambda_base = 0.0035
kappa = 0.065
omega0 = 0.18
xi = 0.015
delta = 0.05
noise = 0.001
w_m = 0.1

# --- Regulation constants ---
phi_c = 1.5          # soft saturation limit
zeta = 0.005         # vacuum energy feedback rate
chi = 0.002          # damping amplification factor

# --- State variables ---
a = np.zeros(T)
H = np.zeros(T)
phi = np.zeros(T)
phid = np.zeros(T)
rho_tot = np.zeros(T)
rho_phi = np.zeros(T)
rho_m = np.zeros(T)
rho_curv = np.zeros(T)
Lambda_eff = np.zeros(T)

# --- Initial conditions ---
a[0] = 1.0
H[0] = -0.25
phi[0] = 0.35
phid[0] = -0.02
Lambda_eff[0] = Lambda_base

# --- Functions ---
def V(phi):
    """Soft-saturation potential preventing runaway φ4."""
    return 0.5 * (omega0 ** 2) * phi ** 2 + beta * phi ** 4 / (1 + (phi ** 2 / phi_c ** 2))

def dV(phi):
    """Derivative of the soft potential."""
    denom = (1 + (phi ** 2 / phi_c ** 2)) ** 2
    return (omega0 ** 2) * phi + 4 * beta * phi ** 3 / (1 + (phi ** 2 / phi_c ** 2)) - \
           2 * beta * phi ** 5 / (phi_c ** 2 * denom)

# --- Simulation loop ---
for i in range(1, T):
    rho_m[i] = kappa / (a[i-1] ** (3 * (1 + w_m)))
    rho_phi[i] = 0.5 * (phid[i-1] ** 2) + V(phi[i-1])
    rho_curv[i] = delta / (a[i-1] ** 2)
    rho_tot[i] = rho_m[i] + rho_phi[i] + rho_curv[i] + Lambda_eff[i-1]

    # --- Energy-derivative feedback on vacuum ---
    if i > 2:
        dE = (rho_tot[i] - rho_tot[i-1]) / dt
    else:
        dE = 0.0
    Lambda_eff[i] = Lambda_base - zeta * dE
    Lambda_eff[i] = np.clip(Lambda_eff[i], -0.01, 0.02)

    # --- Energy-weighted damping ---
    xi_eff = xi * (1 + chi * min(rho_tot[i], 1e3))

    # --- Friedmann-like update ---
    H[i] = H[i-1] + dt * (-alpha * rho_m[i] + Lambda_eff[i] - xi_eff * H[i-1])
    a[i] = max(1e-6, a[i-1] + a[i-1] * H[i] * dt)

    # --- Scalar field dynamics ---
    phidd = -3 * H[i] * phid[i-1] - dV(phi[i-1])
    phid[i] = phid[i-1] + dt * phidd + np.random.normal(0, noise)
    phi[i] = phi[i-1] + dt * phid[i]

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
if a_min > 0.05 and mean_coherence > 0.6 and energy_max < 500:
    verdict = "✅ Stable Bounce (Dynamic Field Regulation)"
elif a_min > 0.02 and mean_coherence > 0.4:
    verdict = "⚠️ Semi-Stable (bounded but oscillatory)"
else:
    verdict = "❌ Collapse or runaway"

# --- Plots ---
plt.figure(figsize=(9, 5))
plt.plot(t, a, label="a(t)")
plt.axvline(t[bounce_index], color="purple", ls="--", label="bounce")
plt.title("F5 - Scale Factor Evolution (Dynamic Field Regulation)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F5_ScaleFactorEvolution.png")

plt.figure(figsize=(9, 5))
plt.plot(t, rho_tot, label="ρ_total", lw=1.3)
plt.plot(t, rho_phi, label="ρ_φ", alpha=0.6)
plt.plot(t, Lambda_eff, "--", label="Λ_eff(t)", alpha=0.7)
plt.yscale("log")
plt.title("F5 - Energy Density and Dynamic Vacuum Feedback")
plt.xlabel("time"); plt.ylabel("Energy (log)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F5_EnergyDecomposition.png")

plt.figure(figsize=(9, 5))
plt.plot(t, np.cos(phi), lw=1.0, label="cos(φ)")
plt.title("F5 - Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F5_PhaseCoherence.png")

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
        "phi_c": phi_c,
        "zeta": zeta,
        "chi": chi
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
        "scale_plot": "FAEV_F5_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F5_EnergyDecomposition.png",
        "phase_plot": "FAEV_F5_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F5_dynamic_field_regulation.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F5 - Dynamic Field Regulation (Stabilized Energy Bounce) ===")
print(f"a_min={a_min:.4f} | mean_coherence={mean_coherence:.3f} | anti-corr(Λ,E)={anti_corr:.2f}")
print(f"-> {verdict}")
print("✅ Results saved -> backend/modules/knowledge/F5_dynamic_field_regulation.json")