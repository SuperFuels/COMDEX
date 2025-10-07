# ==========================================================
# G4-RC2 — Entropy–Information Lock (Λ-Feedback Coupling)
# Tessaris Unified Equation (TUE) refinement stage
# Goal: establish phase-locked equilibrium between entropy S(t)
#       and information flux I(t), while dynamically stabilizing
#       Λ_eff and curvature-energy balance.
# Saves: backend/modules/knowledge/G4RC2_entropy_info_lock.json
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from scipy.ndimage import gaussian_filter1d

# ---- Load constants (or defaults) ----
try:
    from backend.photon_algebra.utils.load_constants import load_constants
    C = load_constants()
except Exception:
    C = {}

ħ   = float(C.get("ħ", 0.001))
G   = float(C.get("G", 1e-5))
Λ   = float(C.get("Lambda_base", 1e-6))
α   = float(C.get("alpha", 0.5))
β   = float(C.get("beta", 0.2))
noise = float(C.get("noise", 2e-4))

# ---- Simulation parameters ----
np.random.seed(42)
T  = 6000
dt = 0.002
t  = np.linspace(0, T*dt, T)

# Feedback control parameters (RC2 tuned)
η_G = 0.0004   # geometry feedback
η_T = 0.0003   # thermal feedback
η_Λ = 0.0005   # vacuum/curvature coupling
γ_sync = 0.002 # S–I synchronizer gain
E_cap = 8.0e4  # energy cap softened slightly

# ---- Initialize fields ----
ψ = np.exp(1j * np.linspace(0, 8*np.pi, T)) + 0.015*np.random.randn(T)
ψ_dot = np.gradient(ψ, dt)

R = np.zeros(T)     # curvature proxy
S = np.zeros(T)     # entropy flux
I = np.zeros(T)     # info flux
E_geom = np.zeros(T)
E_therm = np.zeros(T)
E_info = np.zeros(T)
E_total = np.zeros(T)

# Effective constants (dynamic)
G_eff, T_eff, Λ_eff = G, 1.0, Λ

def soft_clip(x, cap):
    return cap * np.tanh(x / max(cap, 1e-9))

# ---- Simulation loop ----
for i in range(2, T):
    # curvature proxy (finite difference)
    R[i] = np.real((ψ[i] - 2*ψ[i-1] + ψ[i-2]) / (dt**2))

    # entropy proxy (positive)
    amp = np.abs(ψ[i])
    S[i] = np.abs(np.sum(amp**2 * np.log(amp**2 + 1e-12)))

    # information flux
    I[i] = np.real(ψ_dot[i] * np.conj(ψ[i]))

    # synchronizer between S and I (entropy–info lock)
    sync_term = γ_sync * (S[i-1] - np.mean(S[max(0, i-50):i])) * I[i-1]
    I[i] -= sync_term  # self-balancing mutual damping

    # energy components
    E_geom[i]  = (R[i] / (8 * np.pi * G_eff))
    E_therm[i] = T_eff * S[i]
    E_info[i]  = ħ * I[i]
    E_total[i] = soft_clip(E_geom[i] + E_therm[i] + E_info[i], E_cap)

    # feedback update with Λ–curvature coupling
    G_eff += -η_G * I[i] * dt
    T_eff +=  η_T * (I[i] - 0.5*S[i]) * dt
    Λ_eff += -η_Λ * (S[i] - np.tanh(R[i])) * dt

# ---- Metrics ----
E_min = float(np.min(E_total))
E_max = float(np.max(E_total))
E_stab = float(1.0 - np.var(E_total) / (1 + np.mean(E_total)**2))
cross_corr = float(np.corrcoef(S, I)[0,1])

if E_stab > 0.92 and abs(cross_corr) > 0.8:
    verdict = "✅ Stable Conservation (Entropy–Information Lock Achieved)"
elif E_stab > 0.7:
    verdict = "⚠️ Partial Coupling (Moderate Stability)"
else:
    verdict = "❌ Divergent or Weak Coupling"

# ---- Smoothed traces for visualization ----
E_total_s = gaussian_filter1d(E_total, sigma=10)
S_s = gaussian_filter1d(S, sigma=10)
I_s = gaussian_filter1d(I, sigma=10)

# ---- Plots ----
plt.figure(figsize=(9,5))
plt.plot(t, E_total_s, lw=1.6, label="E_total (smoothed)")
plt.title("G4-RC2 — Energy Conservation (Entropy–Information Lock)")
plt.xlabel("time"); plt.ylabel("E_total"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC2_EnergyConservation.png")

plt.figure(figsize=(9,5))
plt.plot(t, S_s, color="orange", lw=1.5, label="Entropy Flux S(t)")
plt.plot(t, I_s, color="purple", lw=1.0, alpha=0.8, label="Information Flux İ(t)")
plt.title("G4-RC2 — Entropy–Information Coupling Dynamics")
plt.xlabel("time"); plt.ylabel("Flux amplitude"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC2_EntropyInfoCoupling.png")

plt.figure(figsize=(9,5))
plt.scatter(S_s[::10], I_s[::10], s=4, alpha=0.6, color="green")
plt.title("G4-RC2 — Phase Portrait: S vs I (Lock Formation)")
plt.xlabel("Entropy Flux S"); plt.ylabel("Information Flux İ"); plt.tight_layout()
plt.savefig("FAEV_G4RC2_PhasePortrait.png")

# ---- Save JSON ----
out = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β, "noise": noise,
        "η_G": η_G, "η_T": η_T, "η_Λ": η_Λ, "γ_sync": γ_sync, "E_cap": E_cap
    },
    "metrics": {
        "energy_min": E_min,
        "energy_max": E_max,
        "energy_stability": E_stab,
        "entropy_info_correlation": cross_corr
    },
    "classification": verdict,
    "files": {
        "energy_plot": "FAEV_G4RC2_EnergyConservation.png",
        "coupling_plot": "FAEV_G4RC2_EntropyInfoCoupling.png",
        "phase_plot": "FAEV_G4RC2_PhasePortrait.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = "backend/modules/knowledge/G4RC2_entropy_info_lock.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== G4-RC2 — Entropy–Information Lock (Λ-Feedback Coupling) ===")
print(f"stability={E_stab:.3f} | corr(S,I)={cross_corr:.3f} | "
      f"E_range=({E_min:.3e},{E_max:.3e})")
print(f"→ {verdict}")
print(f"✅ Results saved → {save_path}")