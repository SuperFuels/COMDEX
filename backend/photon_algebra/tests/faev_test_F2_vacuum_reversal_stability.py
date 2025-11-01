# ==========================================================
# F2 - Vacuum Reversal Stability (Dynamic Λ-field coupling)
# Advanced Cosmology: Singularity Bounce with adaptive vacuum response
# ==========================================================

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- Simulation Parameters ---
np.random.seed(99)
T = 2800                     # time steps
dt = 0.002
eta = 0.001
a0 = 1.0
adot0 = -0.22                # slightly slower contraction

# Physical constants (normalized)
alpha = 0.7       # gravitational term (reduced)
beta = 0.15       # radiation-like repulsion
Lambda_base = 0.0035  # baseline vacuum energy
kappa = 0.065     # vacuum-phase coupling (stronger)
omega0 = 0.2      # base phase frequency
xi = 0.015        # curvature-phase feedback
delta = 0.05      # damping on phase
noise = 0.0012    # vacuum noise

# --- Arrays ---
t = np.linspace(0, T*dt, T)
a = np.zeros(T)
adot = np.zeros(T)
addot = np.zeros(T)
phi = np.zeros(T)
Lambda_t = np.zeros(T)

a[0] = a0
adot[0] = adot0
phi[0] = 0.0

# --- Dynamic vacuum adjustment function ---
def adaptive_Lambda(a_val):
    """Vacuum amplification near minimal scale factor."""
    return Lambda_base * (1 + 0.8 * np.exp(-((a_val - 0.15)**2) / 0.02))

# --- Simulation loop ---
for i in range(1, T):
    # adaptive vacuum
    Lambda_t[i] = adaptive_Lambda(a[i-1])

    # effective densities
    rho_m = 1.0 / (a[i-1]**3 + 1e-6)
    rho_v = Lambda_t[i] * np.cos(phi[i-1])
    pressure = rho_v - 0.33 * rho_m

    # second derivative of scale factor
    addot[i] = -alpha * rho_m * a[i-1] + beta / (a[i-1]**3 + 1e-6) - Lambda_t[i] * a[i-1]**3 + kappa * np.sin(phi[i-1])
    adot[i] = adot[i-1] + addot[i] * dt
    a[i] = max(1e-6, a[i-1] + adot[i] * dt)

    # phase evolution with curvature feedback
    curvature_term = xi / (a[i]**2 + 1e-6)
    dphi = (omega0 + curvature_term - delta * np.sin(phi[i-1])) * dt + np.random.normal(0, noise)
    phi[i] = phi[i-1] + dphi

# --- Metrics ---
a_min = np.min(a)
a_max = np.max(a)
R_bounce = np.argmin(a)
energy_total = alpha / (2*a**2) + beta / (2*a**4) + 0.5*Lambda_t*a**2
energy_min = float(np.min(energy_total))
energy_max = float(np.max(energy_total))
mean_coherence = float(np.mean(np.cos(phi)))
coherence_stability = float(np.std(np.cos(phi[-400:])))

# --- Classification ---
if a_min > 0.05 and coherence_stability < 0.06 and energy_max < 200:
    verdict = "✅ Stable Singularity Bounce (Vacuum Reversal Achieved)"
elif a_min > 0.02 and energy_max < 500:
    verdict = "⚠️ Chaotic Rebound (partial coherence)"
else:
    verdict = "❌ Vacuum Collapse (no rebound)"

# --- Plots ---
plt.figure(figsize=(9, 5))
plt.plot(t, a, label='Scale factor a(t)', lw=1.5)
plt.axvline(t[R_bounce], color='purple', ls='--', alpha=0.7, label='Bounce')
plt.title("F2 - Scale Factor Evolution (Vacuum Reversal Stability)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F2_ScaleFactorEvolution.png")

plt.figure(figsize=(9, 5))
plt.plot(t, energy_total, label='Total Energy Density', lw=1.2)
plt.plot(t, Lambda_t * 100, "gray", ls='--', alpha=0.7, label='Scaled Λ(t)')
plt.title("F2 - Energy Density and Dynamic Vacuum Λ(t)")
plt.xlabel("time"); plt.ylabel("Energy (arb. units)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F2_EnergyDensity.png")

plt.figure(figsize=(9, 5))
plt.plot(t, np.cos(phi), lw=1.0, label='cos(φ)')
plt.title("F2 - Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F2_PhaseCoherence.png")

# --- Save Results ---
results = {
    "eta": eta,
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
        "noise": noise
    },
    "metrics": {
        "a_min": float(a_min),
        "a_max": float(a_max),
        "bounce_index": int(R_bounce),
        "energy_min": energy_min,
        "energy_max": energy_max,
        "mean_coherence": mean_coherence,
        "coherence_stability": coherence_stability
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_F2_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F2_EnergyDensity.png",
        "phase_plot": "FAEV_F2_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F2_vacuum_reversal_stability.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F2 - Vacuum Reversal Stability (Dynamic Λ-field coupling) ===")
print(f"a_min={a_min:.4f} | mean_coherence={mean_coherence:.3f} | energy_range=({energy_min:.3e},{energy_max:.3e})")
print(f"-> {verdict}")
print("✅ Results saved -> backend/modules/knowledge/F2_vacuum_reversal_stability.json")