# ==========================================================
# F1 — Singularity Bounce (Full Dynamic Mode)
# Cosmological scale-factor evolution with vacuum–field coupling
# ==========================================================

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- Simulation Parameters ---
np.random.seed(42)
T = 2400                     # time steps
dt = 0.002                   # step size
eta = 0.001                  # integration step (for damping)
a0 = 1.0                     # initial scale factor
adot0 = -0.25                # initial contraction velocity

# Physical constants (normalized)
alpha = 0.8      # matter gravity term
beta = 0.15      # radiation-like repulsion
Lambda = 0.0018  # vacuum energy density
kappa = 0.02     # phase–field coupling
omega0 = 0.2     # base field frequency
xi = 0.015       # curvature–phase coupling
delta = 0.07     # damping on field phase
noise = 0.0015   # stochastic vacuum fluctuation scale

# --- Arrays ---
t = np.linspace(0, T*dt, T)
a = np.zeros(T)
adot = np.zeros(T)
addot = np.zeros(T)
phi = np.zeros(T)

a[0] = a0
adot[0] = adot0
phi[0] = 0.0

# --- Simulation loop ---
for i in range(1, T):
    # effective densities
    rho_m = 1.0 / (a[i-1]**3 + 1e-6)
    rho_v = Lambda * np.cos(phi[i-1])
    pressure = rho_v - 0.33 * rho_m

    # second derivative of scale factor
    addot[i] = -alpha * rho_m * a[i-1] + beta / (a[i-1]**3 + 1e-6) - Lambda * a[i-1]**3 + kappa * np.sin(phi[i-1])
    # integrate
    adot[i] = adot[i-1] + addot[i] * dt
    a[i] = max(1e-6, a[i-1] + adot[i] * dt)  # prevent negative a

    # vacuum field phase evolution
    dphi = (omega0 + xi / (a[i]**2 + 1e-6) - delta * np.sin(phi[i-1])) * dt + np.random.normal(0, noise)
    phi[i] = phi[i-1] + dphi

# --- Metrics ---
a_min = np.min(a)
a_max = np.max(a)
R_bounce = np.argmin(a)
energy_total = alpha / (2*a**2) + beta / (2*a**4) + 0.5*Lambda*a**2
energy_min = float(np.min(energy_total))
energy_max = float(np.max(energy_total))
mean_coherence = float(np.mean(np.cos(phi)))
coherence_stability = float(np.std(np.cos(phi[-400:])))

# --- Classification ---
if a_min > 0.02 and coherence_stability < 0.05 and energy_max < 20:
    verdict = "✅ Stable Singularity Bounce"
elif a_min > 0.0 and energy_max < 100:
    verdict = "⚠️ Chaotic Rebound (partial coherence loss)"
else:
    verdict = "❌ Vacuum Collapse (no rebound)"

# --- Plots ---
plt.figure(figsize=(9, 5))
plt.plot(t, a, label='Scale factor a(t)', lw=1.5)
plt.axvline(t[R_bounce], color='purple', ls='--', alpha=0.7, label='Bounce')
plt.title("F1 — Scale Factor Evolution (Singularity Bounce)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F1_ScaleFactorEvolution.png")

plt.figure(figsize=(9, 5))
plt.plot(t, energy_total, label='Energy density (total)', lw=1.2)
plt.title("F1 — Total Energy Density Evolution")
plt.xlabel("time"); plt.ylabel("Energy (arb. units)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F1_EnergyDensity.png")

plt.figure(figsize=(9, 5))
plt.plot(t, np.cos(phi), lw=1.0, label='cos(φ)')
plt.title("F1 — Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F1_PhaseCoherence.png")

# --- Save JSON Results ---
results = {
    "eta": eta,
    "dt": dt,
    "T": T,
    "constants": {
        "alpha": alpha,
        "beta": beta,
        "Lambda": Lambda,
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
        "scale_plot": "FAEV_F1_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F1_EnergyDensity.png",
        "phase_plot": "FAEV_F1_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F1_singularity_bounce.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F1 — Singularity Bounce (Full Dynamic Mode) ===")
print(f"a_min={a_min:.4f} | mean_coherence={mean_coherence:.3f} | energy_range=({energy_min:.3e},{energy_max:.3e})")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/F1_singularity_bounce.json")