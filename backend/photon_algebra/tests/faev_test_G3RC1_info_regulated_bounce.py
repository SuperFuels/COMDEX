# ==========================================================
# G3-RC1 — Information-Regulated Antigravity Bounce
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from backend.photon_algebra.utils.load_constants import load_constants

# --- Load constants with defaults ---
C = load_constants()
ħ   = C.get("ħ", 1e-3)
G   = C.get("G", 1e-5)
Λ   = C.get("Λ", 1e-6)
α   = C.get("α", 0.5)
β   = C.get("β", 0.2)
ω0  = C.get("omega0", 0.18)
noise = C.get("noise", 6e-4)

# --- Parameters ---
np.random.seed(42)
T, dt = 4000, 0.002
t = np.linspace(0, T*dt, T)

# Couplings
k_eq = 0.035
k_sync = 0.030
k_neg = 0.020
γd = 0.003
ρc = 1.0

# New adaptive feedback terms
κ_info = 0.015   # strength of info regulation
k_infoR = 0.010  # info-coupled curvature response
k_infoM = 0.008  # info-coupled mass response

# --- State arrays ---
a = np.zeros(T); a[0] = 1.0
adot = np.zeros(T); adot[0] = -0.18
R = np.zeros(T)
Rψ = np.zeros(T)
Mψ = np.zeros(T); Mψ[0] = 0.3
φ = np.zeros(T)
ψ = np.zeros(T)
E_tot = np.zeros(T)

# --- Helper ---
def sat(x, xcrit): return x/(1+abs(x)/xcrit)

# --- Simulation loop ---
for i in range(1, T):
    ρ_m = 1.0/(a[i-1]**3 + 1e-9)
    ρ_v = Λ*np.cos(φ[i-1])
    ρ_ψ = -k_neg*Mψ[i-1]*np.cos(ψ[i-1])
    ρ = ρ_m + ρ_v + ρ_ψ
    ρ_eff = sat(ρ, ρc)

    addot = -(α*ρ_m)*a[i-1] + β/(a[i-1]**3+1e-9) - Λ*a[i-1]**3 \
            + 0.05*np.sin(φ[i-1]) + 0.04*np.sin(ψ[i-1])
    adot[i] = adot[i-1] + addot*dt
    a[i] = max(1e-6, a[i-1] + adot[i]*dt)

    # --- Curvatures ---
    R[i] = sat(addot/(a[i-1]+1e-9), 10.0)

    # information flux & phase difference
    dφ = (ω0 - γd*np.sin(φ[i-1]))*dt + np.random.normal(0, noise)
    dψ = (ω0*0.9 - γd*np.sin(ψ[i-1]))*dt + np.random.normal(0, noise*0.8)
    φ[i] = φ[i-1] + dφ
    ψ[i] = ψ[i-1] + dψ
    Δφ = φ[i] - ψ[i]
    I_flow = ħ*(dφ - dψ)/dt

    # hidden curvature with info feedback
    feedback = k_infoR * np.tanh(I_flow*100) + κ_info*np.sin(Δφ)
    Rψ[i] = Rψ[i-1] + dt*(k_eq*(R[i] - Rψ[i-1]) + feedback)

    # hidden mass evolution (includes polarity flip correction)
    mod = (1 - k_infoM*np.sin(Δφ))
    Mψ[i] = Mψ[i-1] + dt*(0.012*(abs(Rψ[i]) - Mψ[i-1]))*mod

    # --- Unified energy (Tessaris components) ---
    E_geom = (1/(8*np.pi*G))*R[i]
    E_ent  = abs(ρ_v)
    E_info = ħ*abs(I_flow)
    E_tot[i] = E_geom + E_ent + E_info

# --- Metrics ---
a_min = float(np.min(a))
a_max = float(np.max(a))
cross_corr = float(np.corrcoef(R[100:], Rψ[100:])[0,1])
E_stab = float(np.std(E_tot[-1000:]))
bounce_idx = int(np.argmin(a))

# --- Classification ---
if a_min > 0.3 and cross_corr > 0.8 and E_stab < 1e4:
    verdict = "✅ Stable Information-Regulated Bounce (Coupled)"
elif cross_corr > 0.4:
    verdict = "⚠️ Partial Coupling (Moderate Info Damping)"
else:
    verdict = "❌ Unstable or Decoupled"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t,a); plt.axvline(t[bounce_idx],ls='--',c='purple',alpha=0.6,label='min(a)')
plt.title("G3-RC1 — Scale Factor Evolution (Info-Regulated Bounce)")
plt.xlabel("time"); plt.ylabel("a(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC1_ScaleFactor.png")

plt.figure(figsize=(9,5))
plt.plot(t,R,label="R (visible)")
plt.plot(t,Rψ,label="Rψ (hidden)")
plt.title("G3-RC1 — Curvature Tracks (R vs Rψ, Info Coupled)")
plt.xlabel("time"); plt.ylabel("curvature"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC1_CurvatureTracks.png")

plt.figure(figsize=(9,5))
plt.plot(t,Mψ,label="Hidden mass Mψ"); plt.title("G3-RC1 — Hidden Mass Evolution (Feedback)")
plt.xlabel("time"); plt.ylabel("Mψ (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC1_HiddenMass.png")

plt.figure(figsize=(9,5))
plt.plot(t,E_tot,label="Unified energy (norm)")
plt.title("G3-RC1 — Unified Energy Evolution (Info-Stabilized)")
plt.xlabel("time"); plt.ylabel("E_total (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC1_Energy.png")

# --- Save JSON ---
data = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β, "ω0": ω0, "noise": noise,
        "k_eq": k_eq, "k_sync": k_sync, "k_neg": k_neg, "γd": γd, "ρc": ρc,
        "κ_info": κ_info, "k_infoR": k_infoR, "k_infoM": k_infoM
    },
    "metrics": {
        "a_min": a_min, "a_max": a_max, "bounce_index": bounce_idx,
        "cross_correlation_R_Rψ": cross_corr,
        "energy_stability": E_stab,
        "energy_min": float(np.min(E_tot)), "energy_max": float(np.max(E_tot))
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_G3RC1_ScaleFactor.png",
        "curvature_plot": "FAEV_G3RC1_CurvatureTracks.png",
        "mass_plot": "FAEV_G3RC1_HiddenMass.png",
        "energy_plot": "FAEV_G3RC1_Energy.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
with open("backend/modules/knowledge/G3RC1_info_regulated_bounce.json","w") as f:
    json.dump(data,f,indent=2)

print("=== G3-RC1 — Information-Regulated Antigravity Bounce ===")
print(f"a_min={a_min:.4f} | cross_corr={cross_corr:.3f} | E_stab={E_stab:.3e}")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/G3RC1_info_regulated_bounce.json")