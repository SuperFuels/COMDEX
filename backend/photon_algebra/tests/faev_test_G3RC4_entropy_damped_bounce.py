# ==========================================================
# G3-RC4 - Entropy-Damped Bounce (Thermodynamic Stabilization)
# ==========================================================
import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from backend.photon_algebra.utils.load_constants import load_constants

C = load_constants()
ħ, G, Λ = C.get("ħ",1e-3), C.get("G",1e-5), C.get("Λ",1e-6)
α, β, ω0, noise = 0.5, 0.2, 0.18, 6e-4

# --- parameters ---
dt, T = 0.002, 6000
t = np.linspace(0, T*dt, T)
k_eq, k_sync, k_neg0 = 0.035, 0.05, 0.02
k_infoR, k_infoM = 0.015, 0.012
γd_base, κΛ, ρc, E_soft = 0.002, 0.018, 1.0, 3e4

# --- initialize state arrays ---
a=np.zeros(T); a[0]=1.0
adot=np.zeros(T); adot[0]=-0.25
R=np.zeros(T); Rψ=np.zeros(T)+0.01
Mψ=np.zeros(T)+0.3; φ=np.zeros(T); ψ=np.zeros(T)
Λ_eff=np.zeros(T)+Λ; E_total=np.zeros(T)

def softcap(E, Emax): return Emax*np.tanh(E/Emax)
def entropy_weight(E_hist):
    # Shannon-like normalized entropy proxy
    E_range = np.ptp(E_hist) + 1e-9
    p = np.abs(E_hist)/E_range
    p /= (np.sum(p)+1e-9)
    S = -np.sum(p*np.log(p+1e-9))
    return np.clip(S/np.log(len(p)+1e-9), 0, 1)

window = 200  # entropy window size

for i in range(1, T):
    ρm = 1/(a[i-1]**3 + 1e-9)
    ρv = Λ_eff[i-1]*np.cos(φ[i-1])
    # compute entropy-damped γd
    if i > window:
        γd = γd_base * (0.5 + 0.5*(1 - entropy_weight(E_total[i-window:i])))
    else:
        γd = γd_base
    dR = (-γd*R[i-1] + k_eq*(Rψ[i-1]-R[i-1])
          + k_sync*np.cos(ψ[i-1]-φ[i-1])
          + k_infoR*np.cos(φ[i-1]))
    dRψ = (k_eq*(R[i-1]-Rψ[i-1])
           + 0.5*k_sync*np.cos(φ[i-1]-ψ[i-1])
           + 0.1*k_infoR*np.cos(ψ[i-1]))
    R[i] = R[i-1] + dR*dt
    Rψ[i] = Rψ[i-1] + dRψ*dt

    dMψ = (-k_infoM*np.tanh(R[i]-Rψ[i]) - 0.002*Mψ[i-1])
    Mψ[i] = max(0.05, Mψ[i-1] + dMψ*dt)

    Λ_eff[i] = np.clip(Λ_eff[i-1] - κΛ*(R[i]-Rψ[i])*dt, -5e-6, 5e-6)

    addot = (-α*ρm*a[i-1] + β/(a[i-1]**3 + 1e-9)
             - Λ_eff[i]*a[i-1]**3
             + k_neg0*(-Mψ[i])*np.tanh(R[i])
             + 0.02*np.sin(ψ[i-1]))
    adot[i] = adot[i-1] + addot*dt
    a[i] = max(1e-4, a[i-1] + adot[i]*dt)

    dφ = (ω0 + 0.02*R[i] - 0.003*np.sin(φ[i-1])
          + 0.02*k_sync*np.sin(ψ[i-1]-φ[i-1]))*dt + np.random.normal(0, noise)
    dψ = (ω0 + 0.02*Rψ[i] - 0.003*np.sin(ψ[i-1])
          + 0.02*k_sync*np.sin(φ[i-1]-ψ[i-1]))*dt + np.random.normal(0, 0.5*noise)
    φ[i] = φ[i-1] + dφ
    ψ[i] = ψ[i-1] + dψ

    E = (R[i]/(8*np.pi*G)) + Λ_eff[i]*ρm*a[i]**3 + ħ*np.cos(φ[i]-ψ[i])
    E_total[i] = softcap(E, E_soft)

# --- metrics ---
a_min, a_max = float(np.min(a)), float(np.max(a))
bounce_idx = int(np.argmin(a))
cross_corr = float(np.corrcoef(R, Rψ)[0,1])
E_stab = float(np.std(E_total[int(0.5*T):]))
S_final = entropy_weight(E_total[int(0.5*T):])

# classification
if cross_corr > 0.9 and E_stab < 1e3 and S_final < 0.6:
    verdict = "✅ Stable Thermodynamic Bounce (Entropy-Regulated)"
elif cross_corr > 0.6 and E_stab < 3e3:
    verdict = "⚠️ Partial Coupling (Moderate Stability)"
else:
    verdict = "❌ Unstable or Decoupled"

# --- plots ---
plt.figure(figsize=(9,5))
plt.plot(t, a); plt.axvline(t[bounce_idx], ls="--", c="purple", alpha=0.6, label="min(a)")
plt.title("G3-RC4 - Scale Factor Evolution (Entropy-Damped Bounce)")
plt.xlabel("time"); plt.ylabel("a(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC4_ScaleFactor.png")

plt.figure(figsize=(9,5))
plt.plot(t, R, label="R (visible)"); plt.plot(t, Rψ, label="Rψ (hidden)")
plt.title("G3-RC4 - Curvature Synchrony (Entropy-Damped)")
plt.xlabel("time"); plt.ylabel("curvature"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC4_Curvature.png")

plt.figure(figsize=(9,5))
plt.plot(t, E_total, label="Unified energy (norm)")
plt.title("G3-RC4 - Unified Energy Evolution (Soft-Capped + Entropy Damping)")
plt.xlabel("time"); plt.ylabel("E_total (norm)")
plt.legend(); plt.tight_layout(); plt.savefig("FAEV_G3RC4_Energy.png")

# --- save results ---
data = {
  "dt": dt, "T": T,
  "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
                "ω0": ω0, "noise": noise,
                "γd_base": γd_base, "κΛ": κΛ, "E_soft": E_soft},
  "metrics": {"a_min": a_min, "a_max": a_max, "bounce_index": bounce_idx,
              "cross_correlation_R_Rψ": cross_corr,
              "energy_stability": E_stab,
              "entropy_final": S_final,
              "energy_min": float(np.min(E_total)),
              "energy_max": float(np.max(E_total))},
  "classification": verdict,
  "files": {"scale_plot": "FAEV_G3RC4_ScaleFactor.png",
            "curvature_plot": "FAEV_G3RC4_Curvature.png",
            "energy_plot": "FAEV_G3RC4_Energy.png"},
  "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
out = "backend/modules/knowledge/G3RC4_entropy_damped_bounce.json"
with open(out, "w") as f: json.dump(data, f, indent=2)

print("=== G3-RC4 - Entropy-Damped Bounce (Thermodynamic Stabilization) ===")
print(f"a_min={a_min:.4f} | cross_corr={cross_corr:.3f} | E_stab={E_stab:.3e} | S_final={S_final:.3f}")
print(f"-> {verdict}")
print(f"✅ Results saved -> {out}")