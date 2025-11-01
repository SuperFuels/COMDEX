# ==========================================================
# G4-RC3 - Λ-Memory Feedback Coupling
# Tessaris Unified Equation (TUE) refinement stage
# Goal: introduce Λ-memory term to link entropy and curvature
#       through delayed feedback, forming a temporal coherence loop.
# Saves: backend/modules/knowledge/G4RC3_lambda_memory_feedback.json
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

# Feedback and memory control parameters
η_G = 0.0004   # geometry feedback
η_T = 0.0003   # thermal feedback
η_Λ = 0.0005   # vacuum coupling base rate
μ_mem = 0.35   # memory weight for delayed entropy feedback
τ = 80         # memory delay (steps)
E_cap = 6.0e4  # moderate energy soft cap

# ---- Initialize fields ----
ψ = np.exp(1j * np.linspace(0, 8*np.pi, T)) + 0.015*np.random.randn(T)
ψ_dot = np.gradient(ψ, dt)

R = np.zeros(T)     # curvature
S = np.zeros(T)     # entropy
I = np.zeros(T)     # information flux
Λ_trace = np.zeros(T)
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
    # curvature proxy
    R[i] = np.real((ψ[i] - 2*ψ[i-1] + ψ[i-2]) / (dt**2))

    # entropy flux
    amp = np.abs(ψ[i])
    S[i] = np.abs(np.sum(amp**2 * np.log(amp**2 + 1e-12)))

    # information flux
    I[i] = np.real(ψ_dot[i] * np.conj(ψ[i])) + np.random.normal(0, noise)

    # Λ-memory backpropagation
    if i > τ:
        dS_mem = S[i] - S[i-τ]
    else:
        dS_mem = 0.0

    Λ_eff += -η_Λ * (S[i] - np.tanh(R[i]) + μ_mem * dS_mem) * dt
    Λ_trace[i] = Λ_eff

    # energy components
    E_geom[i]  = (R[i] / (8 * np.pi * G_eff))
    E_therm[i] = T_eff * S[i]
    E_info[i]  = ħ * I[i]
    E_total[i] = soft_clip(E_geom[i] + E_therm[i] + E_info[i], E_cap)

    # feedback on other constants
    G_eff += -η_G * I[i] * dt
    T_eff +=  η_T * (I[i] - 0.3*S[i]) * dt

# ---- Metrics ----
E_min = float(np.min(E_total))
E_max = float(np.max(E_total))
E_stab = float(1.0 - np.var(E_total) / (1 + np.mean(E_total)**2))
corr_SI = float(np.corrcoef(S, I)[0,1])
corr_RΛ = float(np.corrcoef(R, Λ_trace)[0,1])

if E_stab > 0.9 and abs(corr_SI) > 0.7 and abs(corr_RΛ) > 0.7:
    verdict = "✅ Stable Conservation (Λ-Memory Coupled Equilibrium)"
elif E_stab > 0.7:
    verdict = "⚠️ Partial Coupling (Λ-memory stabilizing)"
else:
    verdict = "❌ Weak Feedback or Divergent Energy"

# ---- Smoothed traces ----
E_total_s = gaussian_filter1d(E_total, sigma=10)
S_s = gaussian_filter1d(S, sigma=10)
I_s = gaussian_filter1d(I, sigma=10)
Λ_s = gaussian_filter1d(Λ_trace, sigma=10)

# ---- Plots ----
plt.figure(figsize=(9,5))
plt.plot(t, E_total_s, lw=1.6, label="E_total (smoothed)")
plt.title("G4-RC3 - Energy Conservation (Λ-Memory Feedback)")
plt.xlabel("time"); plt.ylabel("E_total"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC3_EnergyConservation.png")

plt.figure(figsize=(9,5))
plt.plot(t, Λ_s, color="green", lw=1.4, label="Λ_eff(t)")
plt.title("G4-RC3 - Λ Evolution (Memory-Driven Feedback)")
plt.xlabel("time"); plt.ylabel("Λ_eff"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC3_LambdaEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(S_s, I_s, '.', alpha=0.4, color="purple", markersize=3)
plt.title("G4-RC3 - Phase Portrait: S vs I (Λ-Memory Coupling)")
plt.xlabel("Entropy Flux S"); plt.ylabel("Information Flux İ"); plt.tight_layout()
plt.savefig("FAEV_G4RC3_PhasePortrait.png")

# ---- Save JSON ----
out = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β, "noise": noise,
        "η_G": η_G, "η_T": η_T, "η_Λ": η_Λ, "μ_mem": μ_mem,
        "τ": τ, "E_cap": E_cap
    },
    "metrics": {
        "energy_min": E_min,
        "energy_max": E_max,
        "energy_stability": E_stab,
        "corr_S_I": corr_SI,
        "corr_R_Lambda": corr_RΛ
    },
    "classification": verdict,
    "files": {
        "energy_plot": "FAEV_G4RC3_EnergyConservation.png",
        "lambda_plot": "FAEV_G4RC3_LambdaEvolution.png",
        "phase_plot": "FAEV_G4RC3_PhasePortrait.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = "backend/modules/knowledge/G4RC3_lambda_memory_feedback.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== G4-RC3 - Λ-Memory Feedback Coupling (TUE Refinement) ===")
print(f"stability={E_stab:.3f} | corr(S,I)={corr_SI:.3f} | corr(R,Λ)={corr_RΛ:.3f} | "
      f"E_range=({E_min:.3e},{E_max:.3e})")
print(f"-> {verdict}")
print(f"✅ Results saved -> {save_path}")