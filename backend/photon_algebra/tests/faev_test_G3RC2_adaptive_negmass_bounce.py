# ==========================================================
# G3-RC2 — Info-Regulated Negative-Mass Bounce (Adaptive)
# Adds: phase-lock control, adaptive Λ_eff, soft saturation,
#       and energy cap to prevent runaway spikes.
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from backend.photon_algebra.utils.load_constants import load_constants

# ---- Constants (shared registry) ----
const = load_constants()
ħ   = const.get("ħ", 1e-3)
G   = const.get("G", 1e-5)
Λ   = const.get("Λ", 1e-6)
α   = const.get("α", 0.5)
β   = const.get("β", 0.2)
ω0  = const.get("omega0", const.get("ω0", 0.18))
noise = const.get("noise", 6e-4)

# ---- Sim params ----
np.random.seed(42)
dt, T = 0.002, 4000
t = np.linspace(0, T*dt, T)

# Controllers (tuned)
k_eq   = 0.035     # curvature–mass equalization
k_sync = 0.05      # visible/hidden phase sync (↑ from RC1)
k_neg0 = 0.02      # base negative-mass coupling
k_infoR = 0.015    # information feedback on curvature (↑)
k_infoM = 0.012    # information feedback on hidden mass (↑)
γd     = 0.004     # damping on R
ρc     = 1.0       # critical density scale (for bounce proxy)
κΛ     = 0.03      # adaptive Λ_eff gain
Λ_clip = 5e-6      # clamp for Λ_eff magnitude
E_cap  = 3.0e4     # soft cap for unified energy

# ---- State arrays ----
a = np.zeros(T); a[0] = 1.0
adot = np.zeros(T); adot[0] = -0.25
R = np.zeros(T)              # visible curvature proxy
Rψ = np.zeros(T) + 0.01      # hidden curvature proxy
Mψ = np.zeros(T) + 0.30      # hidden effective mass (norm)
φ = np.zeros(T); ψ = np.zeros(T)
Λ_eff = np.zeros(T) + Λ

E_total = np.zeros(T)

# Helpers
def softclip(x, lo, hi):  # smooth-ish clamp
    return lo + (hi-lo) * (1/(1+np.exp(-8*(x - (lo+hi)/2)/(hi-lo))))

# ---- Main loop ----
for i in range(1, T):
    # densities and pressure proxies
    rho_m = 1.0 / (a[i-1]**3 + 1e-9)
    rho_v = Λ_eff[i-1] * np.cos(φ[i-1])
    pressure = rho_v - 0.33 * rho_m

    # curvature dynamics (visible & hidden)
    # target: R tracks Rψ (curvature–mass equivalence + sync)
    dR  = (-γd*R[i-1] 
           + k_eq*(Rψ[i-1] - R[i-1])
           + k_sync*np.cos(ψ[i-1]-φ[i-1])
           + k_infoR*np.cos(φ[i-1]))  # info feedback
    dRψ = ( k_eq*(R[i-1]-Rψ[i-1])
           + 0.5*k_sync*np.cos(φ[i-1]-ψ[i-1])
           + 0.1*k_infoR*np.cos(ψ[i-1]) )
    R[i]  = R[i-1]  + dR*dt
    Rψ[i] = Rψ[i-1] + dRψ*dt

    # hidden mass evolution (negative-mass regulator)
    # move Mψ to reduce |R-Rψ| and leakage
    dMψ = ( -k_infoM*np.tanh(R[i]-Rψ[i])
            - 0.002*Mψ[i-1] )
    Mψ[i] = max(0.05, Mψ[i-1] + dMψ*dt)  # keep positive floor for stability

    # adaptive Λ_eff to counter spikes (anti-runaway)
    Λ_eff[i] = np.clip(Λ_eff[i-1] - κΛ*(R[i]-Rψ[i])*dt, -Λ_clip, Λ_clip)

    # scale factor acceleration with negative-mass term
    # add bounce-like ρ_c regulator term
    addot = (-α*rho_m*a[i-1] + β/(a[i-1]**3 + 1e-9)
             - Λ_eff[i]*a[i-1]**3
             + k_neg0*(-Mψ[i])*np.tanh(R[i])  # effective antigravity
             + 0.02*np.sin(ψ[i-1]))           # small coupling assist

    # integrate a(t)
    adot[i] = adot[i-1] + addot*dt
    a[i] = max(1e-4, a[i-1] + adot[i]*dt)

    # phases with mild noise; lock via k_sync
    dφ = (ω0 + 0.02*R[i] - 0.003*np.sin(φ[i-1])
          + 0.02*k_sync*np.sin(ψ[i-1]-φ[i-1]))*dt + np.random.normal(0, noise)
    dψ = (ω0 + 0.02*Rψ[i] - 0.003*np.sin(ψ[i-1])
          + 0.02*k_sync*np.sin(φ[i-1]-ψ[i-1]))*dt + np.random.normal(0, 0.5*noise)
    φ[i] = φ[i-1] + dφ
    ψ[i] = ψ[i-1] + dψ

    # unified energy (soft-capped to avoid numeric blow-up)
    E_geom = (c := 299792458.0); pref = (c**4)/(8*np.pi*G)
    E_geom *= 0  # (keep namespace clean; we’ll just use pref*R)
    E = pref*R[i] + (Λ_eff[i]*rho_m*a[i]**3) + ħ*np.cos(φ[i]-ψ[i])
    # soft cap
    E_total[i] = np.sign(E) * min(abs(E), E_cap)

# ---- Metrics ----
a_min = float(np.min(a)); a_max = float(np.max(a))
bounce_idx = int(np.argmin(a))
cross_corr = float(np.corrcoef(R, Rψ)[0,1])
E_stab = float(np.std(E_total[int(0.5*T):]))

# Classification
if a_min > 0.32 and cross_corr > 0.65 and E_stab < 2.0e3:
    verdict = "✅ Stable Info-Regulated Negative-Mass Bounce"
elif a_min > 0.25 and cross_corr > 0.45 and E_stab < 6.0e3:
    verdict = "⚠️ Partial Coupling (near-bounce)"
else:
    verdict = "❌ Unstable or Decoupled"

# ---- Plots ----
plt.figure(figsize=(9,5))
plt.plot(t, a); plt.axvline(t[bounce_idx], ls='--', c='purple', alpha=0.7, label='min(a)')
plt.title("G3-RC2 — Scale Factor Evolution (Adaptive Neg-Mass)")
plt.xlabel("time"); plt.ylabel("a(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC2_ScaleFactor.png")

plt.figure(figsize=(9,5))
plt.plot(t, R, label="R (visible)"); plt.plot(t, Rψ, label="Rψ (hidden)")
plt.title("G3-RC2 — Curvature Tracks (R vs Rψ)")
plt.xlabel("time"); plt.ylabel("curvature"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC2_CurvatureTracks.png")

plt.figure(figsize=(9,5))
plt.plot(t, Mψ, label="Hidden mass Mψ")
plt.title("G3-RC2 — Hidden Effective Mass Evolution")
plt.xlabel("time"); plt.ylabel("Mψ (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC2_HiddenMass.png")

plt.figure(figsize=(9,5))
plt.plot(t, E_total, label="Unified energy (norm)")
plt.title("G3-RC2 — Unified Energy Evolution (Capped)"); plt.legend()
plt.xlabel("time"); plt.ylabel("E_total (norm)"); plt.tight_layout()
plt.savefig("FAEV_G3RC2_Energy.png")

# ---- Save JSON ----
results = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "ω0": ω0, "noise": noise,
        "k_eq": k_eq, "k_sync": k_sync, "k_neg0": k_neg0,
        "κΛ": κΛ, "Λ_clip": Λ_clip,
        "k_infoR": k_infoR, "k_infoM": k_infoM,
        "γd": γd, "ρc": ρc, "E_cap": E_cap
    },
    "metrics": {
        "a_min": a_min, "a_max": a_max, "bounce_index": bounce_idx,
        "cross_correlation_R_Rψ": cross_corr, "energy_stability": E_stab,
        "energy_min": float(np.min(E_total)), "energy_max": float(np.max(E_total))
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_G3RC2_ScaleFactor.png",
        "curvature_plot": "FAEV_G3RC2_CurvatureTracks.png",
        "mass_plot": "FAEV_G3RC2_HiddenMass.png",
        "energy_plot": "FAEV_G3RC2_Energy.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
outpath = "backend/modules/knowledge/G3RC2_adaptive_negmass_bounce.json"
with open(outpath, "w") as f:
    json.dump(results, f, indent=2)

print("=== G3-RC2 — Information-Regulated Negative-Mass Bounce (Adaptive) ===")
print(f"a_min={a_min:.4f} | cross_corr={cross_corr:.3f} | E_stab={E_stab:.3e}")
print(f"→ {verdict}")
print(f"✅ Results saved → {outpath}")