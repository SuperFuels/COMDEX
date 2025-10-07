import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==========================================================
# F7 — Entangled Geometry Confinement (Nonlocal Quantum Memory)
# ==========================================================

np.random.seed(42)

# --- Simulation parameters ---
dt = 0.002
T = 4000
t = np.arange(T) * dt

# --- Physical constants ---
alpha = 0.7
beta = 0.08
Lambda_base = 0.0035
kappa = 0.065
omega0 = 0.18
xi = 0.015
delta = 0.05
noise = 0.001
w_m = 0.1

# --- Quantum feedback constants ---
eta_Q = 0.015      # backreaction
zeta_Q = 0.004     # vacuum derivative
xi_Q = 0.0008      # quantum noise

# --- Nonlocal geometry memory constants ---
eta_E = 0.02       # memory coupling strength
tau_E = 0.12       # memory time window
lambda_E = 18.0    # exponential decay of memory influence

# --- Arrays ---
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

# --- Initial conditions ---
a[0] = 1.0
H[0] = -0.25
phi[0] = 0.35
phid[0] = -0.02
Lambda_eff[0] = Lambda_base

# --- Helper functions ---
def V(phi):
    return 0.5 * (omega0 ** 2) * phi ** 2 + beta * phi ** 4 / (1 + phi ** 2)

def dV(phi):
    return (omega0 ** 2) * phi + 4 * beta * phi ** 3 / (1 + phi ** 2) - \
           2 * beta * phi ** 5 / ((1 + phi ** 2) ** 2)

# --- Simulation loop ---
for i in range(1, T):
    rho_m[i] = kappa / (a[i-1] ** (3 * (1 + w_m)))
    rho_phi[i] = 0.5 * (phid[i-1] ** 2) + V(phi[i-1])
    rho_curv[i] = delta / (a[i-1] ** 2 + 1e-6)
    rho_tot[i] = rho_m[i] + rho_phi[i] + rho_curv[i] + Lambda_eff[i-1]

    # Derivative for Λ feedback
    dE = (rho_tot[i] - rho_tot[i-1]) / dt if i > 1 else 0.0
    Lambda_eff[i] = Lambda_eff[i-1] - zeta_Q * dE + np.random.normal(0, xi_Q)
    Lambda_eff[i] = np.clip(Lambda_eff[i], -0.01, 0.02)

    # Compute dH
    if i > 2:
        dH = (H[i-1] - H[i-2]) / dt
    else:
        dH = 0.0

    # --- Nonlocal memory kernel ---
    if i > int(tau_E / dt):
        window = int(tau_E / dt)
        weights = np.exp(-lambda_E * np.linspace(0, tau_E, window))
        dH_hist = np.diff(H[i-window:i])
        Q_mem[i] = -eta_E * np.sum(dH_hist * weights[:-1]) * dt
    else:
        Q_mem[i] = 0.0

    # --- Update Hubble parameter ---
    H[i] = H[i-1] + dt * (-alpha * rho_m[i] + Lambda_eff[i] - xi * H[i-1] + Q_mem[i])
    a[i] = max(1e-6, a[i-1] + a[i-1] * H[i] * dt)

    # --- Scalar field evolution ---
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
anti_corr = float(np.corrcoef(rho_tot, -Lambda_eff)[0, 1])

# --- Classification ---
if a_min > 0.08 and mean_coherence > 0.6:
    verdict = "✅ Stable Entangled Bounce (Geometry Confinement Achieved)"
elif a_min > 0.04:
    verdict = "⚠️ Partial rebound (nonlocal damping present)"
else:
    verdict = "❌ Collapse or decoherence"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, a, label="a(t)")
plt.axvline(t[bounce_index], color="purple", ls="--", label="bounce")
plt.title("F7 — Scale Factor Evolution (Entangled Geometry Confinement)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7_ScaleFactorEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(t, rho_tot, label="ρ_total", lw=1.3)
plt.plot(t, rho_phi, label="ρ_φ", alpha=0.6)
plt.plot(t, Lambda_eff, "--", label="Λ_eff(t)", alpha=0.7)
plt.yscale("log")
plt.title("F7 — Energy Density and Entangled Vacuum Feedback")
plt.xlabel("time"); plt.ylabel("Energy (log)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7_EnergyDecomposition.png")

plt.figure(figsize=(9,5))
plt.plot(t, np.cos(phi), lw=1.0, label="cos(φ)")
plt.title("F7 — Vacuum-Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(φ)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7_PhaseCoherence.png")

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
        "eta_Q": eta_Q,
        "zeta_Q": zeta_Q,
        "xi_Q": xi_Q,
        "eta_E": eta_E,
        "tau_E": tau_E,
        "lambda_E": lambda_E
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
        "scale_plot": "FAEV_F7_ScaleFactorEvolution.png",
        "energy_plot": "FAEV_F7_EnergyDecomposition.png",
        "phase_plot": "FAEV_F7_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F7_entangled_geometry_confinement.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F7 — Entangled Geometry Confinement (Nonlocal Quantum Memory) ===")
print(f"a_min={a_min:.4f} | mean_coherence={mean_coherence:.3f} | anti-corr(Λ,E)={anti_corr:.2f}")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/F7_entangled_geometry_confinement.json")