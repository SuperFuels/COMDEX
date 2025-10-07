# ==========================================================
# G3 — Negative-Mass / Antigravity Bounce (Dark-Sector ψ)
# Curvature–mass equivalence with hidden negative-mass drive
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from backend.photon_algebra.utils.load_constants import load_constants

# --- Constants (with safe fallbacks) ---
C = load_constants()
ħ   = C.get("ħ", 1e-3)
G   = C.get("G", 1e-5)
Λ   = C.get("Λ", 1e-6)
α   = C.get("α", 0.5)
β   = C.get("β", 0.2)
ω0  = C.get("omega0", 0.18)
noise = C.get("noise", 6e-4)

# Dark-sector controls
k_eq   = 0.035     # R↔Rψ tracking gain (curvature–mass equiv.)
k_sync = 0.030     # phase sync φ↔ψ
k_neg  = 0.020     # negative-mass (antigravity) strength
ρc     = 1.0       # LQC-like critical density for bounce regularization
γd     = 0.003     # mild damping on phases

# --- Simulation params ---
np.random.seed(42)
T  = 4000
dt = 0.002
t  = np.linspace(0, T*dt, T)

# State
a      = np.zeros(T);  a[0] = 1.0
adot   = np.zeros(T);  adot[0] = -0.20
φ      = np.zeros(T);  φ[0] = 0.0        # visible phase
ψ      = np.zeros(T);  ψ[0] = 0.2        # hidden phase
R      = np.zeros(T)
Rψ     = np.zeros(T)
Mψ     = np.zeros(T);  Mψ[0] = 0.3       # effective hidden mass (can go negative)
E_tot  = np.zeros(T)

# Helpers
def saturation(x, xcrit):
    # loop-quantum-cosmology–style regulator:  x / (1 + |x|/xcrit)
    return x / (1.0 + np.abs(x)/xcrit)

for i in range(1, T):
    # Curvatures: visible ~ ä/a ; hidden ~ k_eq*R + antigravity from negative mass
    # Visible sector (toy Friedmann with regulator)
    ρ_m  = 1.0 / (a[i-1]**3 + 1e-9)
    ρ_v  = Λ * np.cos(φ[i-1])
    ρ_ψ  = -k_neg * Mψ[i-1] * np.cos(ψ[i-1])          # negative-mass contribution
    ρ    = ρ_m + ρ_v + ρ_ψ
    ρ_eff = saturation(ρ, ρc)

    # acceleration (toy Raychaudhuri + phase kick)
    addot = -(α*ρ_m)*a[i-1] + β/(a[i-1]**3 + 1e-9) - Λ*a[i-1]**3 \
            + 0.04*np.sin(φ[i-1]) + 0.03*np.sin(ψ[i-1])

    # integrate a
    adot[i] = adot[i-1] + addot*dt
    a[i]    = max(1e-6, a[i-1] + adot[i]*dt)

    # curvature proxies
    R[i]  = saturation(addot/(a[i-1] + 1e-9), 10.0)
    # hidden curvature tries to track R but with its own dynamics and antigravity bias
    Rψ[i] = Rψ[i-1] + dt*(k_eq*(R[i] - Rψ[i-1]) + 0.02*np.sin(ψ[i-1]))

    # hidden effective mass evolves toward curvature magnitude (equivalence) but
    # can flip sign via ψ and info flow
    info_flow = ħ * (np.cos(φ[i-1]) - np.cos(ψ[i-1]))
    dM = dt*( 0.015*(np.abs(Rψ[i]) - Mψ[i-1]) - 0.01*np.sin(ψ[i-1]) + 0.5*info_flow )
    Mψ[i] = Mψ[i-1] + dM

    # phases with mild sync and damping + noise
    dφ = (ω0 + 0.015/(a[i]**2 + 1e-9) - γd*np.sin(φ[i-1]) + k_sync*np.sin(ψ[i-1]-φ[i-1]))*dt \
         + np.random.normal(0, noise)
    dψ = (ω0*0.9 + 0.012*np.abs(Rψ[i]) - γd*np.sin(ψ[i-1]) + k_sync*np.sin(φ[i-1]-ψ[i-1]))*dt \
         + np.random.normal(0, noise*0.9)
    φ[i] = φ[i-1] + dφ
    ψ[i] = ψ[i-1] + dψ

    # unified energy (normalized) using Tessaris identity (toy units)
    E_geom = (1.0/(8*np.pi*G)) * R[i]         # c^4 absorbed into units
    E_ent  = (1.0) * (np.abs(ρ_v))            # k_B T_eff S ~ |ρ_v| proxy
    E_info = ħ * (np.cos(φ[i]) - np.cos(ψ[i]))/dt
    E_tot[i] = E_geom + E_ent + E_info

# --- Metrics ---
a_min = float(np.min(a)); a_max = float(np.max(a))
bounce_idx = int(np.argmin(a))
cross_corr = float(np.corrcoef(R[50:], Rψ[50:])[0,1]) if np.std(Rψ[50:])>0 else 0.0
energy_stab = float(np.std(E_tot[-500:]))

# classification
if a_min > 0.45 and cross_corr > 0.85 and energy_stab < 1e3:
    verdict = "✅ Stable Antigravity-Assisted Bounce (Coupled)"
elif a_min > 0.1 and cross_corr > 0.5:
    verdict = "⚠️ Partial Bounce with Weak Coupling"
else:
    verdict = "❌ No Bounce / Decoupled"

# --- Plots ---
plt.figure(figsize=(9,5))
plt.plot(t, a); plt.axvline(t[bounce_idx], ls='--', c='purple', alpha=0.6, label='min(a)')
plt.title("G3 — Scale Factor Evolution (Antigravity-Driven)"); plt.xlabel("time"); plt.ylabel("a(t)"); plt.legend()
plt.tight_layout(); plt.savefig("FAEV_G3_ScaleFactor.png")

plt.figure(figsize=(9,5))
plt.plot(t, R, label="R (visible)"); plt.plot(t, Rψ, label="Rψ (hidden)")
plt.title("G3 — Curvature Tracks (R vs Rψ)"); plt.xlabel("time"); plt.ylabel("curvature"); plt.legend()
plt.tight_layout(); plt.savefig("FAEV_G3_CurvatureTracks.png")

plt.figure(figsize=(9,5))
plt.plot(t, Mψ, label="Hidden mass Mψ"); plt.title("G3 — Hidden Effective Mass Evolution")
plt.xlabel("time"); plt.ylabel("Mψ (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3_HiddenMass.png")

plt.figure(figsize=(9,5))
plt.plot(t, E_tot, label="Unified energy (norm)")
plt.title("G3 — Unified Energy Evolution"); plt.xlabel("time"); plt.ylabel("E_total (norm)")
plt.legend(); plt.tight_layout(); plt.savefig("FAEV_G3_Energy.png")

# --- Save JSON ---
out = {
    "dt": dt, "T": T,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
                  "ω0": ω0, "noise": noise,
                  "k_eq": k_eq, "k_sync": k_sync, "k_neg": k_neg,
                  "ρc": ρc, "γd": γd},
    "metrics": {
        "a_min": a_min, "a_max": a_max, "bounce_index": bounce_idx,
        "cross_correlation_R_Rψ": cross_corr, "energy_stability": energy_stab,
        "energy_min": float(np.min(E_tot)), "energy_max": float(np.max(E_tot))
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_G3_ScaleFactor.png",
        "curvature_plot": "FAEV_G3_CurvatureTracks.png",
        "mass_plot": "FAEV_G3_HiddenMass.png",
        "energy_plot": "FAEV_G3_Energy.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
with open("backend/modules/knowledge/G3_negative_mass_bounce.json","w") as f:
    json.dump(out, f, indent=2)

print("=== G3 — Negative-Mass / Antigravity Bounce ===")
print(f"a_min={a_min:.4f} | cross_corr={cross_corr:.3f} | E_stab={energy_stab:.3e}")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/G3_negative_mass_bounce.json")