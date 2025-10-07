# ==========================================================
# G2 — Curvature–Mass Equivalence (Baseline Coupled Sectors)
# Tests unified exchange between visible curvature R and
# hidden-sector effective mass M_ψ via Tessaris unified law.
# ==========================================================

import json, numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- Constants loader (Tessaris style) ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ   = const.get("ħ", 1e-3)
G   = const.get("G", 1e-5)
Λ   = const.get("Λ", 1e-6)
α   = const.get("α", 0.55)
β   = const.get("β", 0.20)

# --- Simulation params (match F/G cadence) ---
np.random.seed(42)
T   = 4000
dt  = 0.002
t   = np.linspace(0, T*dt, T)

# state arrays
R      = np.zeros(T)   # visible curvature proxy
Rψ     = np.zeros(T)   # hidden curvature proxy
Mψ     = np.zeros(T)   # hidden effective mass
E_tot  = np.zeros(T)   # unified energy (normalized)

# controls (gentle; we’ll tune in RC steps later)
k_x    = 0.035   # curvature–mass transfer gain
k_rel  = 0.012   # relaxation of hidden mass to curvature
k_leak = 0.004   # leakage / dissipation
noise  = const.get("noise", 6e-4)

# initialize (start slightly curved hidden sector)
R[0]   = 0.0
Rψ[0]  = 0.72
Mψ[0]  = 0.3

# helper: unified energy density (scaled)
c = const.get("c", 1.0)
kB = const.get("kB", 1.0)
Teff = const.get("T_eff", 1.0)
Sx = const.get("S_base", 1.0)

def unified_energy(Rt, Rpsit, Mpsit):
    geom = (c**4/(8*np.pi*G))*Rt
    matter = kB*Teff*Sx + Mpsit*c**2
    info = ħ*0.0  # (no explicit info flow in baseline)
    # keep in numeric range
    return 1e-34*(geom + matter + info)

# --- Dynamics loop ---
for i in range(1, T):
    # coupling: visible curvature converts to hidden mass (and back)
    dMψ   = (k_x*R[i-1] - k_leak*Mψ[i-1] + k_rel*(Rψ[i-1]-R[i-1]))*dt
    dR    = (α*Rψ[i-1] - β*R[i-1] - Λ + np.random.normal(0, noise))*dt
    dRψ   = (α*R[i-1]  - β*Rψ[i-1] - k_x*Mψ[i-1])*dt

    Mψ[i] = max(0.0, Mψ[i-1] + dMψ)
    R[i]  = R[i-1] + dR
    Rψ[i] = Rψ[i-1] + dRψ

    E_tot[i] = unified_energy(R[i], Rψ[i], Mψ[i])

# --- Metrics ---
cross_corr = float(np.corrcoef(R, Rψ)[0,1])
energy_min, energy_max = float(np.min(E_tot)), float(np.max(E_tot))
stability = float(np.std(np.diff(E_tot[-800:])))  # small = steadier

# classification heuristics
if cross_corr > 0.8 and stability < 0.05:
    verdict = "✅ Curvature–Mass Equivalence (Stable Coupling)"
elif cross_corr > 0.4 and stability < 0.2:
    verdict = "⚠️ Partial Coupling (needs damping)"
else:
    verdict = "❌ Decoupled or Unstable"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, R,  label="Visible curvature R")
plt.plot(t, Rψ, label="Hidden curvature Rψ")
plt.title("G2 — Curvature–Mass Equivalence (R vs Rψ)")
plt.xlabel("time"); plt.ylabel("curvature"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G2_CurvatureTracks.png")

plt.figure(figsize=(9,5))
plt.plot(t, Mψ, lw=1.5, label="Hidden mass Mψ")
plt.title("G2 — Hidden Effective Mass Evolution")
plt.xlabel("time"); plt.ylabel("Mψ (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G2_HiddenMass.png")

plt.figure(figsize=(9,5))
plt.plot(t, E_tot, lw=1.2, label="Unified energy")
plt.title("G2 — Unified Energy Evolution (Baseline)")
plt.xlabel("time"); plt.ylabel("E_total (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G2_Energy.png")

# --- Save JSON ---
results = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "k_x": k_x, "k_rel": k_rel, "k_leak": k_leak, "noise": noise
    },
    "metrics": {
        "cross_correlation_R_Rψ": cross_corr,
        "energy_min": energy_min, "energy_max": energy_max,
        "energy_stability": stability
    },
    "classification": verdict,
    "files": {
        "curvature_plot": "FAEV_G2_CurvatureTracks.png",
        "mass_plot": "FAEV_G2_HiddenMass.png",
        "energy_plot": "FAEV_G2_Energy.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
with open("backend/modules/knowledge/G2_curvature_mass_equivalence.json","w") as f:
    json.dump(results, f, indent=2)

print("=== G2 — Curvature–Mass Equivalence (Baseline) ===")
print(f"cross_corr={cross_corr:.3f} | stability={stability:.3f} | energy=({energy_min:.3e},{energy_max:.3e})")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/G2_curvature_mass_equivalence.json")