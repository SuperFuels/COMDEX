import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==============================================================
# F7b-R+ — Entropy / Information Flux Tracking
# Refined Dual-Field Quantum Bounce with Entropy Metric
# ==============================================================

np.random.seed(42)

# --- Parameters ---
dt = 0.002
T = 12000  # double duration for longer observation
t = np.arange(T) * dt

# --- Physical constants ---
alpha = 0.7
beta = 0.08
Lambda_base = 0.0035
kappa = 0.065
omega0 = 0.18
xi = 0.015
delta = 0.05
noise = 0.0006
rho_c = 1.0
g_couple = 0.015
kp, ki, kd = 0.2, 0.005, 0.04
Lambda_rate_max = 0.0004

# --- Arrays ---
a = np.zeros(T)
H = np.zeros(T)
phi1, phi2 = np.zeros(T), np.zeros(T)
phid1, phid2 = np.zeros(T), np.zeros(T)
rho_tot, rho_phi, Lambda_eff = np.zeros(T), np.zeros(T), np.zeros(T)
entropy_flux = np.zeros(T)
Lambda_eff[0] = Lambda_base

integral_err, prev_err = 0.0, 0.0

# --- Initial conditions ---
a[0] = 1.0
H[0] = -0.25
phi1[0], phi2[0] = 0.3, -0.25
phid1[0], phid2[0] = -0.02, 0.015

# --- Potential & derivative ---
def V(phi):
    return 0.5 * (omega0 ** 2) * phi ** 2 + beta * phi ** 4 / (1 + phi ** 2 / 2.5 ** 2)

def dV(phi):
    d = (omega0 ** 2) * phi + 4 * beta * phi ** 3 / (1 + phi ** 2 / 2.5 ** 2)
    d -= 2 * beta * phi ** 5 / ((2.5 ** 2) * (1 + phi ** 2 / 2.5 ** 2) ** 2)
    return np.tanh(d / 5.0) * 5.0

# --- Simulation ---
for i in range(1, T):
    dt_eff = dt / (1 + 20 * abs(H[i - 1]))
    V1, V2 = V(phi1[i - 1]), V(phi2[i - 1])
    E_int = g_couple * phi1[i - 1] * phi2[i - 1]
    rho_phi[i] = 0.5 * (phid1[i - 1] ** 2 + phid2[i - 1] ** 2) + V1 + V2 + E_int
    rho_m = kappa / (a[i - 1] ** (3 * (1 + 0.1)))
    rho_curv = delta / (a[i - 1] ** 2 + 1e-6)
    rho_tot[i] = np.clip(rho_m + rho_phi[i] + rho_curv + Lambda_eff[i - 1], 0, 1.5 * rho_c)

    # --- LQC correction ---
    H_sq = rho_tot[i] * (1 - rho_tot[i] / rho_c)
    H[i] = np.sign(H[i - 1]) * np.sqrt(abs(H_sq)) if H_sq >= 0 else 0.0

    # --- PID feedback ---
    err = (rho_c / 2) - rho_tot[i]
    integral_err += err * dt_eff
    d_err = (err - prev_err) / dt_eff
    dΛ = np.clip(kp * err + ki * integral_err + kd * d_err, -Lambda_rate_max, Lambda_rate_max)
    Λ_bound = 0.02 * (1 + 0.5 * np.tanh(rho_tot[i]))
    Lambda_eff[i] = np.clip(Lambda_eff[i - 1] + dΛ, -Λ_bound, Λ_bound)
    prev_err = err

    # --- Scale factor evolution ---
    a[i] = max(1e-6, a[i - 1] + a[i - 1] * H[i] * dt_eff)

    # --- Dual-field dynamics ---
    phidd1 = -3 * H[i] * phid1[i - 1] - dV(phi1[i - 1]) - g_couple * (phi1[i - 1] - phi2[i - 1])
    phidd2 = -3 * H[i] * phid2[i - 1] - dV(phi2[i - 1]) - g_couple * (phi2[i - 1] - phi1[i - 1])
    phid1[i] = phid1[i - 1] + dt_eff * phidd1 + np.random.normal(0, noise)
    phid2[i] = phid2[i - 1] + dt_eff * phidd2 + np.random.normal(0, noise)
    phi1[i] = phi1[i - 1] + dt_eff * phid1[i]
    phi2[i] = phi2[i - 1] + dt_eff * phid2[i]
    phi1[i], phi2[i] = np.clip(phi1[i], -6, 6), np.clip(phi2[i], -6, 6)

    # --- Entropy / information flux ---
    phase_diff = np.cos(phi1[i] - phi2[i])
    phase_var = np.var(np.cos(phi1[:i] - phi2[:i])) + 1e-8
    energy_grad = abs(rho_tot[i] - rho_tot[i - 1]) + 1e-12
    entropy_flux[i] = np.log(1 + (energy_grad / (1 + phase_var)))

# --- Metrics ---
a_min, a_max = float(np.min(a)), float(np.max(a))
bounce_index = int(np.argmin(a))
mean_coherence = float(np.mean(np.cos(phi1 - phi2)))
coherence_stability = float(np.std(np.cos(phi1 - phi2)))
anti_corr = float(np.corrcoef(rho_tot, -Lambda_eff)[0, 1])
mean_entropy_flux = float(np.mean(entropy_flux))
entropy_growth = float(entropy_flux[-1] - entropy_flux[0])

# --- Classification ---
if a_min > 0.05 and mean_coherence > 0.8:
    verdict = "✅ Stable Entropic Bounce (High Coherence)"
elif a_min > 0.02:
    verdict = "⚠️ Soft Bounce / Weak Entropy Retention"
else:
    verdict = "❌ Collapse or Decoherence"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, entropy_flux, label="Entropy Flux", color="crimson")
plt.title("F7b-R+ — Information / Entropy Flux over Time")
plt.xlabel("time"); plt.ylabel("S(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7bR_EntropyFlux.png")

plt.figure(figsize=(9,5))
plt.plot(t, np.cos(phi1 - phi2), label="cos(Δφ)")
plt.title("F7b-R+ — Vacuum Field Phase Coherence")
plt.xlabel("time"); plt.ylabel("cos(Δφ)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7bR_PhaseCoherence.png")

# --- Save results ---
results = {
    "constants": {
        "alpha": alpha, "beta": beta, "Lambda_base": Lambda_base,
        "kappa": kappa, "omega0": omega0, "xi": xi, "delta": delta,
        "noise": noise, "rho_c": rho_c, "g_couple": g_couple
    },
    "metrics": {
        "a_min": a_min, "a_max": a_max, "mean_coherence": mean_coherence,
        "coherence_stability": coherence_stability,
        "anti_corr_Lambda_vs_E": anti_corr,
        "mean_entropy_flux": mean_entropy_flux,
        "entropy_growth": entropy_growth
    },
    "classification": verdict,
    "files": {
        "entropy_plot": "FAEV_F7bR_EntropyFlux.png",
        "phase_plot": "FAEV_F7bR_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F7bR_entropy_flux.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F7b-R+ — Entropy / Information Flux Tracking ===")
print(f"a_min={a_min:.4f} | coherence={mean_coherence:.3f} | mean_entropy_flux={mean_entropy_flux:.5f}")
print(f"entropy_growth={entropy_growth:.5f} | anti-corr(Λ,E)={anti_corr:.2f}")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/F7bR_entropy_flux.json")