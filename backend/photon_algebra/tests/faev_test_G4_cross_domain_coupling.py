# ==========================================================
# G4 — Cross-Domain Coupling (Tessaris Unified Equation)
# Goal: enforce conservation of geometric, thermodynamic,
#       and informational energies under dynamic feedback.
# Saves: backend/modules/knowledge/G4_cross_domain_coupling.json
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

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
noise = float(C.get("noise", 6e-4))

# ---- Simulation params ----
np.random.seed(42)
T  = 6000
dt = 0.002
t  = np.linspace(0, T*dt, T)

# Feedback controls
η_G = 0.01   # gravitational feedback
η_T = 0.008  # thermal feedback
η_Λ = 0.005  # vacuum feedback
E_cap = 3.0e4  # energy soft cap

# ---- State arrays ----
ψ = np.exp(1j * np.linspace(0, 6*np.pi, T)) + 0.05*np.random.randn(T)
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
    """Soft tanh cap to avoid runaway energy magnitudes."""
    return cap * np.tanh(x / max(cap, 1e-9))

# ---- Simulation loop ----
for i in range(2, T):
    # curvature proxy (second-order finite difference, scalar-safe)
    R[i] = np.real((ψ[i] - 2*ψ[i-1] + ψ[i-2]) / (dt**2))

    # entropy proxy (Shannon–von Neumann analogue)
    amp = np.abs(ψ[i])
    S[i] = -np.sum(amp**2 * np.log(amp**2 + 1e-12))

    # info flux (mutual information flow)
    I[i] = np.real(ψ_dot[i] * np.conj(ψ[i]))

    # energy components
    E_geom[i]  = (R[i] / (8 * np.pi * G_eff))
    E_therm[i] = T_eff * S[i]
    E_info[i]  = ħ * I[i]
    E_total[i] = soft_clip(E_geom[i] + E_therm[i] + E_info[i], E_cap)

    # dynamic renormalization feedback
    G_eff += -η_G * I[i] * dt
    T_eff +=  η_T * I[i] * dt
    Λ_eff += -η_Λ * (S[i] - 0.5) * dt

# ---- Metrics ----
E_min = float(np.min(E_total))
E_max = float(np.max(E_total))
E_stab = float(1.0 - np.var(E_total) / (1 + np.mean(E_total)**2))
cross_corr = float(np.corrcoef(E_geom, E_info)[0,1])

if E_stab > 0.95 and abs(np.mean(E_total)) < 1e-5:
    verdict = "✅ Stable Conservation (Triune Coupling Achieved)"
elif E_stab > 0.7:
    verdict = "⚠️ Partial Coupling (Moderate Feedback Stability)"
else:
    verdict = "❌ Divergent Feedback (Unstable Equilibrium)"

# ---- Plots ----
plt.figure(figsize=(9,5))
plt.plot(t, E_total, lw=1.6, label="E_total")
plt.title("G4 — Energy Conservation (Tessaris Unified Equation)")
plt.xlabel("time"); plt.ylabel("E_total"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4_EnergyConservation.png")

plt.figure(figsize=(9,5))
plt.plot(t, S, color="orange", lw=1.5, label="Entropy Flux S(t)")
plt.title("G4 — Entropy Flux Evolution")
plt.xlabel("time"); plt.ylabel("S(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4_EntropyFlux.png")

plt.figure(figsize=(9,5))
plt.plot(t, I, color="purple", lw=1.5, label="Information Flux İ(t)")
plt.title("G4 — Information Coupling Dynamics")
plt.xlabel("time"); plt.ylabel("İ(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4_InfoCoupling.png")

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
        "energy_plot": "FAEV_G4_EnergyConservation.png",
        "entropy_plot": "FAEV_G4_EntropyFlux.png",
        "info_plot": "FAEV_G4_InfoCoupling.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = "backend/modules/knowledge/G4_cross_domain_coupling.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== G4 — Cross-Domain Coupling (Tessaris Unified Equation) ===")
print(f"stability={E_stab:.3f} | cross_corr={cross_corr:.3f} | "
      f"E_range=({E_min:.3e},{E_max:.3e})")
print(f"→ {verdict}")
print(f"✅ Results saved → {save_path}")