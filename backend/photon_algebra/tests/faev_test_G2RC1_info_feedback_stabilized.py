# ==========================================================
# G2-RC1 — Curvature–Mass Equivalence with Information Feedback
# Refined model introducing entropic damping + phase-based info coupling
# ==========================================================

import json, numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- Constants loader ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ   = const.get("ħ", 1e-3)
G   = const.get("G", 1e-5)
Λ   = const.get("Λ", 1e-6)
α   = const.get("α", 0.55)
β   = const.get("β", 0.20)
noise = const.get("noise", 6e-4)

# --- Simulation params ---
np.random.seed(42)
T = 4000
dt = 0.002
t = np.linspace(0, T*dt, T)

# --- State arrays ---
R = np.zeros(T)
Rψ = np.zeros(T)
Mψ = np.zeros(T)
φ = np.zeros(T)   # phase variable for info feedback
E_tot = np.zeros(T)

# --- Coupling coefficients ---
k_x = 0.035     # curvature–mass exchange
k_rel = 0.012   # relaxation term
k_leak = 0.004  # energy leak
γ_info = 0.005  # entropic damping gain
k_phase = 0.01  # information-phase coupling
ω0 = 0.18       # base frequency

# --- Initialize ---
R[0], Rψ[0], Mψ[0] = 0.0, 0.7, 0.3
φ[0] = 0.0

# --- Unified energy function ---
def unified_energy(Rt, Rpsit, Mpsit, phit):
    geom = (1/(8*np.pi*G)) * (Rt + Rpsit)
    matter = Mpsit * (1 + np.cos(phit)) * 0.5
    info = ħ * np.abs(np.sin(phit)) * 0.5
    return 1e-33 * (geom + matter + info)

# --- Simulation loop ---
for i in range(1, T):
    # --- Phase evolution (information flux) ---
    dφ = (ω0 - γ_info * np.sin(φ[i-1])) * dt + np.random.normal(0, noise*0.2)
    φ[i] = φ[i-1] + dφ

    # --- Coupled dynamics ---
    phase_mod = 1 + k_phase * np.sin(φ[i-1])
    dMψ = (k_x * R[i-1] - k_leak * Mψ[i-1] + k_rel * (Rψ[i-1] - R[i-1])) * dt
    dR = (α * Rψ[i-1] - β * R[i-1] - Λ - γ_info * R[i-1] * np.abs(np.cos(φ[i-1]))) * dt
    dRψ = (α * R[i-1] - β * Rψ[i-1] - k_x * Mψ[i-1] * phase_mod) * dt

    # --- Integrate ---
    Mψ[i] = max(0.0, Mψ[i-1] + dMψ)
    R[i] = R[i-1] + dR
    Rψ[i] = Rψ[i-1] + dRψ
    E_tot[i] = unified_energy(R[i], Rψ[i], Mψ[i], φ[i])

# --- Metrics ---
cross_corr = float(np.corrcoef(R, Rψ)[0,1])
energy_min, energy_max = float(np.min(E_tot)), float(np.max(E_tot))
stability = 1.0 / (1.0 + np.std(E_tot[-1000:]) / (np.mean(np.abs(E_tot[-1000:])) + 1e-9))

# --- Classification ---
if cross_corr > 0.95 and stability > 0.9:
    verdict = "✅ Information-Stabilized Curvature–Mass Coupling (Coherent)"
elif cross_corr > 0.7:
    verdict = "⚠️ Partial Coupling (Moderate Info Response)"
else:
    verdict = "❌ Unstable or Decoupled"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, R, label="Visible curvature R", lw=1.2)
plt.plot(t, Rψ, label="Hidden curvature Rψ", lw=1.0)
plt.title("G2-RC1 — Curvature–Mass Equivalence (Info Feedback)")
plt.xlabel("time"); plt.ylabel("curvature"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G2RC1_CurvatureTracks.png")

plt.figure(figsize=(9,5))
plt.plot(t, Mψ, label="Hidden mass Mψ", lw=1.3)
plt.title("G2-RC1 — Hidden Mass Evolution with Info Feedback")
plt.xlabel("time"); plt.ylabel("Mψ (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G2RC1_MassEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(t, E_tot, label="Unified energy", lw=1.1)
plt.title("G2-RC1 — Unified Energy Evolution (Info-Stabilized)")
plt.xlabel("time"); plt.ylabel("E_total (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G2RC1_Energy.png")

# --- Save JSON ---
results = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "k_x": k_x, "k_rel": k_rel, "k_leak": k_leak,
        "γ_info": γ_info, "k_phase": k_phase, "ω0": ω0, "noise": noise
    },
    "metrics": {
        "cross_correlation_R_Rψ": cross_corr,
        "energy_min": energy_min, "energy_max": energy_max,
        "energy_stability": stability
    },
    "classification": verdict,
    "files": {
        "curvature_plot": "FAEV_G2RC1_CurvatureTracks.png",
        "mass_plot": "FAEV_G2RC1_MassEvolution.png",
        "energy_plot": "FAEV_G2RC1_Energy.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
with open("backend/modules/knowledge/G2RC1_info_feedback_stabilized.json","w") as f:
    json.dump(results, f, indent=2)

print("=== G2-RC1 — Curvature–Mass Equivalence (Info Feedback) ===")
print(f"cross_corr={cross_corr:.3f} | stability={stability:.3f} | energy=({energy_min:.3e},{energy_max:.3e})")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/G2RC1_info_feedback_stabilized.json")