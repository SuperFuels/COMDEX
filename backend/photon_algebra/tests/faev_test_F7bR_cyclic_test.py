import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==============================================================
# F7b-RC — Multi-Bounce Cyclic Evolution Test
# Refined Dual-Field Quantum Bounce with Recurrent Entropy Tracking
# ==============================================================

np.random.seed(42)

# --- Simulation parameters ---
dt = 0.002
T = 60000   # long-duration simulation (≈ 10x prior)
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
cycle_index = np.zeros(T)

Lambda_eff[0] = Lambda_base
integral_err, prev_err = 0.0, 0.0

# --- Initial conditions ---
a[0] = 1.0
H[0] = -0.25
phi1[0], phi2[0] = 0.3, -0.25
phid1[0], phid2[0] = -0.02, 0.015

# --- Potential ---
def V(phi):
    return 0.5 * (omega0 ** 2) * phi ** 2 + beta * phi ** 4 / (1 + phi ** 2 / 2.5 ** 2)

def dV(phi):
    d = (omega0 ** 2) * phi + 4 * beta * phi ** 3 / (1 + phi ** 2 / 2.5 ** 2)
    d -= 2 * beta * phi ** 5 / ((2.5 ** 2) * (1 + phi ** 2 / 2.5 ** 2) ** 2)
    return np.tanh(d / 5.0) * 5.0

# --- Tracking containers ---
bounce_times = []
entropy_per_cycle = []
coherence_per_cycle = []

# --- Simulation loop ---
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

    # --- PID feedback for Λ_eff ---
    err = (rho_c / 2) - rho_tot[i]
    integral_err += err * dt_eff
    d_err = (err - prev_err) / dt_eff
    dΛ = np.clip(kp * err + ki * integral_err + kd * d_err, -Lambda_rate_max, Lambda_rate_max)
    Λ_bound = 0.02 * (1 + 0.5 * np.tanh(rho_tot[i]))
    Lambda_eff[i] = np.clip(Lambda_eff[i - 1] + dΛ, -Λ_bound, Λ_bound)
    prev_err = err

    # --- Scale factor evolution ---
    a[i] = max(1e-6, a[i - 1] + a[i - 1] * H[i] * dt_eff)

    # --- Dual-field evolution ---
    phidd1 = -3 * H[i] * phid1[i - 1] - dV(phi1[i - 1]) - g_couple * (phi1[i - 1] - phi2[i - 1])
    phidd2 = -3 * H[i] * phid2[i - 1] - dV(phi2[i - 1]) - g_couple * (phi2[i - 1] - phi1[i - 1])
    phid1[i] = phid1[i - 1] + dt_eff * phidd1 + np.random.normal(0, noise)
    phid2[i] = phid2[i - 1] + dt_eff * phidd2 + np.random.normal(0, noise)
    phi1[i] = phi1[i - 1] + dt_eff * phid1[i]
    phi2[i] = phi2[i - 1] + dt_eff * phid2[i]
    phi1[i], phi2[i] = np.clip(phi1[i], -6, 6), np.clip(phi2[i], -6, 6)

    # --- Entropy flux ---
    phase_diff = np.cos(phi1[i] - phi2[i])
    energy_grad = abs(rho_tot[i] - rho_tot[i - 1])
    entropy_flux[i] = np.log(1 + energy_grad / (1 + abs(phase_diff - 1e-6)))

    # --- Bounce detection ---
    if i > 10 and H[i - 1] < 0 and H[i] >= 0:
        bounce_times.append(t[i])
        cycle_index[i:] += 1
        # measure coherence/entropy at each bounce
        coherence_now = np.mean(np.cos(phi1[max(0, i-500):i] - phi2[max(0, i-500):i]))
        entropy_now = np.mean(entropy_flux[max(0, i-500):i])
        coherence_per_cycle.append(coherence_now)
        entropy_per_cycle.append(entropy_now)

# --- Metrics ---
a_min, a_max = float(np.min(a)), float(np.max(a))
num_bounces = len(bounce_times)
mean_coherence = float(np.mean(coherence_per_cycle)) if num_bounces > 0 else 0
entropy_drift = float(entropy_flux[-1] - entropy_flux[0])
entropy_cycle_mean = float(np.mean(entropy_per_cycle)) if num_bounces > 0 else 0
cycle_coherence_decay = (
    float(coherence_per_cycle[-1] / coherence_per_cycle[0])
    if len(coherence_per_cycle) > 1 else 1.0
)

# --- Classification ---
if num_bounces >= 3 and cycle_coherence_decay > 0.8:
    verdict = "✅ Sustained Multi-Bounce Stability (Information Retained)"
elif num_bounces >= 2:
    verdict = "⚠️ Quasi-Periodic (Mild Decoherence)"
else:
    verdict = "❌ Single Bounce or Collapse"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, a, label="a(t)")
for b in bounce_times:
    plt.axvline(b, ls='--', color='purple', alpha=0.5)
plt.title("F7b-RC — Scale Factor Evolution (Multi-Bounce Cycles)")
plt.xlabel("time"); plt.ylabel("a(t)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_F7bR_Cyclic_ScaleFactor.png")

plt.figure(figsize=(9,5))
plt.plot(t, entropy_flux, color="red", lw=0.8)
plt.title("F7b-RC — Entropy Flux Evolution Across Bounces")
plt.xlabel("time"); plt.ylabel("S(t)")
plt.tight_layout()
plt.savefig("FAEV_F7bR_Cyclic_EntropyFlux.png")

plt.figure(figsize=(7,5))
plt.plot(range(len(coherence_per_cycle)), coherence_per_cycle, marker='o')
plt.title("F7b-RC — Coherence Retention per Bounce")
plt.xlabel("Bounce #"); plt.ylabel("<cos Δφ>")
plt.tight_layout()
plt.savefig("FAEV_F7bR_Cyclic_CoherencePerBounce.png")

# --- Save results ---
results = {
    "metrics": {
        "a_min": a_min, "a_max": a_max,
        "num_bounces": num_bounces,
        "mean_coherence": mean_coherence,
        "entropy_cycle_mean": entropy_cycle_mean,
        "entropy_drift": entropy_drift,
        "cycle_coherence_decay": cycle_coherence_decay
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_F7bR_Cyclic_ScaleFactor.png",
        "entropy_plot": "FAEV_F7bR_Cyclic_EntropyFlux.png",
        "coherence_plot": "FAEV_F7bR_Cyclic_CoherencePerBounce.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/F7bR_cyclic_test.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== F7b-RC — Multi-Bounce Cyclic Evolution ===")
print(f"num_bounces={num_bounces} | mean_coherence={mean_coherence:.3f} | cycle_decay={cycle_coherence_decay:.3f}")
print(f"entropy_mean={entropy_cycle_mean:.5f} | entropy_drift={entropy_drift:.5f}")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/F7bR_cyclic_test.json")