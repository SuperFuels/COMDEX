# ==========================================================
# G4-RC1 - Stabilized Cross-Domain Coupling
# (Tessaris Unified Equation - Λ-Renormalization Test)
# Goal: stabilize triune feedback loop (geometry-entropy-info)
#       under dynamic effective-constant renormalization.
# Saves: backend/modules/knowledge/G4RC1_stabilized_feedback.json
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from scipy.ndimage import gaussian_filter1d

# ---- (Optional) pull shared constants, else fall back to defaults ----
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

# ---- Simulation params ----
np.random.seed(42)
T  = 6000
dt = 0.002
t  = np.linspace(0, T*dt, T)

# Feedback controls (stabilized)
η_G = 0.0005   # gravitational feedback
η_T = 0.0004   # thermal feedback
η_Λ = 0.0003   # vacuum feedback
E_cap = 1.0e5  # soft energy limit

# ---- State arrays ----
ψ = np.exp(1j * np.linspace(0, 6*np.pi, T)) + 0.02*np.random.randn(T)
ψ_dot = np.gradient(ψ, dt)

R = np.zeros(T)     # geometric curvature
S = np.zeros(T)     # entropy
I = np.zeros(T)     # info flux
E_geom = np.zeros(T)
E_therm = np.zeros(T)
E_info = np.zeros(T)
E_total = np.zeros(T)

# Initial effective constants
G_eff, T_eff, Λ_eff = G, 1.0, Λ

def soft_clip(x, cap):
    return cap * np.tanh(x / max(cap, 1e-9))

# ---- Simulation loop ----
for i in range(2, T):
    # curvature proxy (finite difference)
    R[i] = np.real((ψ[i] - 2*ψ[i-1] + ψ[i-2]) / (dt**2))

    # positive entropy proxy
    amp = np.abs(ψ[i])
    S[i] = np.abs(np.sum(amp**2 * np.log(amp**2 + 1e-12)))

    # info flux (mutual information rate proxy)
    I[i] = np.real(ψ_dot[i] * np.conj(ψ[i]))

    # energy decomposition
    E_geom[i]  = (R[i] / (8 * np.pi * G_eff))
    E_therm[i] = T_eff * S[i]
    E_info[i]  = ħ * I[i]
    E_total[i] = soft_clip(E_geom[i] + E_therm[i] + E_info[i], E_cap)

    # dynamic feedback (stabilized)
    G_eff += -η_G * I[i] * dt
    T_eff +=  η_T * I[i] * dt
    Λ_eff += -η_Λ * (S[i] - 0.5) * dt

# ---- Metrics ----
E_min = float(np.min(E_total))
E_max = float(np.max(E_total))
E_stab = float(1.0 - np.var(E_total) / (1 + np.mean(E_total)**2))
cross_corr = float(np.corrcoef(E_geom, E_info)[0,1])

if E_stab > 0.95:
    verdict = "✅ Stable Conservation (Triune Coupling Achieved)"
elif E_stab > 0.75:
    verdict = "⚠️ Partial Coupling (Moderate Feedback Stability)"
else:
    verdict = "❌ Divergent Feedback (Unstable Equilibrium)"

# ---- Smoothing for visualization ----
E_total_s = gaussian_filter1d(E_total, sigma=10)
S_s = gaussian_filter1d(S, sigma=10)
I_s = gaussian_filter1d(I, sigma=10)

# ---- Plots ----
plt.figure(figsize=(9,5))
plt.plot(t, E_total_s, lw=1.6, label="E_total (smoothed)")
plt.title("G4-RC1 - Energy Conservation (Stabilized Feedback)")
plt.xlabel("time"); plt.ylabel("E_total"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC1_EnergyConservation.png")

plt.figure(figsize=(9,5))
plt.plot(t, S_s, color="orange", lw=1.5, label="Entropy Flux S(t)")
plt.title("G4-RC1 - Entropy Flux Evolution (Stabilized)")
plt.xlabel("time"); plt.ylabel("S(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC1_EntropyFlux.png")

plt.figure(figsize=(9,5))
plt.plot(t, I_s, color="purple", lw=1.5, label="Information Flux İ(t)")
plt.title("G4-RC1 - Information Coupling Dynamics (Stabilized)")
plt.xlabel("time"); plt.ylabel("İ(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC1_InfoCoupling.png")

# ---- Save JSON ----
out = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β, "noise": noise,
        "η_G": η_G, "η_T": η_T, "η_Λ": η_Λ, "E_cap": E_cap
    },
    "metrics": {
        "energy_min": E_min,
        "energy_max": E_max,
        "energy_stability": E_stab,
        "cross_correlation_R_I": cross_corr
    },
    "classification": verdict,
    "files": {
        "energy_plot": "FAEV_G4RC1_EnergyConservation.png",
        "entropy_plot": "FAEV_G4RC1_EntropyFlux.png",
        "info_plot": "FAEV_G4RC1_InfoCoupling.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = "backend/modules/knowledge/G4RC1_stabilized_feedback.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== G4-RC1 - Stabilized Cross-Domain Coupling (TUE Feedback) ===")
print(f"stability={E_stab:.3f} | cross_corr={cross_corr:.3f} | "
      f"E_range=({E_min:.3e},{E_max:.3e})")
print(f"-> {verdict}")
print(f"✅ Results saved -> {save_path}")