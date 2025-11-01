# ==========================================================
# G3-RC3 - Open Energy Feedback (Soft-Capped Bounce)
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from backend.photon_algebra.utils.load_constants import load_constants

C = load_constants()
ħ = C.get("ħ", 1e-3); G = C.get("G", 1e-5)
Λ = C.get("Λ", 1e-6); α = C.get("α", 0.5); β = C.get("β", 0.2)
ω0 = C.get("omega0", 0.18); noise = C.get("noise", 6e-4)

# ---- parameters ----
np.random.seed(42)
dt, T = 0.002, 6000
t = np.linspace(0, T*dt, T)

k_eq, k_sync, k_neg0 = 0.035, 0.05, 0.02
k_infoR, k_infoM = 0.015, 0.012
γd, ρc, κΛ = 0.002, 1.0, 0.02
Λ_clip, E_soft = 5e-6, 3.0e4

# ---- state arrays ----
a=np.zeros(T); a[0]=1.0
adot=np.zeros(T); adot[0]=-0.25
R=np.zeros(T); Rψ=np.zeros(T)+0.01
Mψ=np.zeros(T)+0.3; φ=np.zeros(T); ψ=np.zeros(T)
Λ_eff=np.zeros(T)+Λ; E_total=np.zeros(T)

# smooth limiter
def softcap(E, Emax):
    return Emax*np.tanh(E/Emax)

for i in range(1,T):
    ρm=1/(a[i-1]**3+1e-9); ρv=Λ_eff[i-1]*np.cos(φ[i-1])
    dR=(-γd*R[i-1]+k_eq*(Rψ[i-1]-R[i-1])
        +k_sync*np.cos(ψ[i-1]-φ[i-1])
        +k_infoR*np.cos(φ[i-1]))
    dRψ=(k_eq*(R[i-1]-Rψ[i-1])
         +0.5*k_sync*np.cos(φ[i-1]-ψ[i-1])
         +0.1*k_infoR*np.cos(ψ[i-1]))
    R[i]=R[i-1]+dR*dt; Rψ[i]=Rψ[i-1]+dRψ*dt

    dMψ=(-k_infoM*np.tanh(R[i]-Rψ[i])-0.002*Mψ[i-1])
    Mψ[i]=max(0.05,Mψ[i-1]+dMψ*dt)

    Λ_eff[i]=np.clip(Λ_eff[i-1]-κΛ*(R[i]-Rψ[i])*dt,-Λ_clip,Λ_clip)

    addot=(-α*ρm*a[i-1]+β/(a[i-1]**3+1e-9)
           -Λ_eff[i]*a[i-1]**3
           +k_neg0*(-Mψ[i])*np.tanh(R[i])
           +0.02*np.sin(ψ[i-1]))
    adot[i]=adot[i-1]+addot*dt
    a[i]=max(1e-4,a[i-1]+adot[i]*dt)

    dφ=(ω0+0.02*R[i]-0.003*np.sin(φ[i-1])
        +0.02*k_sync*np.sin(ψ[i-1]-φ[i-1]))*dt+np.random.normal(0,noise)
    dψ=(ω0+0.02*Rψ[i]-0.003*np.sin(ψ[i-1])
        +0.02*k_sync*np.sin(φ[i-1]-ψ[i-1]))*dt+np.random.normal(0,0.5*noise)
    φ[i]=φ[i-1]+dφ; ψ[i]=ψ[i-1]+dψ

    E= (R[i]/(8*np.pi*G)) + Λ_eff[i]*ρm*a[i]**3 + ħ*np.cos(φ[i]-ψ[i])
    E_total[i]=softcap(E,E_soft)

# ---- metrics ----
a_min=float(np.min(a)); a_max=float(np.max(a))
bounce_idx=int(np.argmin(a))
cross_corr=float(np.corrcoef(R,Rψ)[0,1])
E_stab=float(np.std(E_total[int(0.5*T):]))

if a_min>0.3 and cross_corr>0.65 and E_stab<2e3:
    verdict="✅ Stable Info-Regulated Bounce (Open Energy)"
elif a_min>0.25 and cross_corr>0.45 and E_stab<6e3:
    verdict="⚠️ Partial Coupling (Moderate)"
else:
    verdict="❌ Unstable or Decoupled"

# ---- plots ----
plt.figure(figsize=(9,5))
plt.plot(t,a); plt.axvline(t[bounce_idx],ls='--',c='purple',alpha=0.6,label='min(a)')
plt.title("G3-RC3 - Scale Factor Evolution (Open Energy Bounce)")
plt.xlabel("time"); plt.ylabel("a(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC3_ScaleFactor.png")

plt.figure(figsize=(9,5))
plt.plot(t,R,label="R (visible)"); plt.plot(t,Rψ,label="Rψ (hidden)")
plt.title("G3-RC3 - Curvature Synchrony (R vs Rψ)")
plt.xlabel("time"); plt.ylabel("curvature"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC3_Curvature.png")

plt.figure(figsize=(9,5))
plt.plot(t,Mψ,label="Hidden mass Mψ")
plt.title("G3-RC3 - Hidden Mass Evolution"); plt.xlabel("time"); plt.ylabel("Mψ")
plt.legend(); plt.tight_layout(); plt.savefig("FAEV_G3RC3_Mass.png")

plt.figure(figsize=(9,5))
plt.plot(t,E_total,label="Unified energy (norm)")
plt.title("G3-RC3 - Unified Energy Evolution (Soft-Capped)")
plt.xlabel("time"); plt.ylabel("E_total (norm)")
plt.legend(); plt.tight_layout(); plt.savefig("FAEV_G3RC3_Energy.png")

# ---- save json ----
data={
  "dt":dt,"T":T,
  "constants":{"ħ":ħ,"G":G,"Λ":Λ,"α":α,"β":β,"ω0":ω0,
               "noise":noise,"γd":γd,"κΛ":κΛ,"E_soft":E_soft},
  "metrics":{"a_min":a_min,"a_max":a_max,"bounce_index":bounce_idx,
             "cross_correlation_R_Rψ":cross_corr,
             "energy_stability":E_stab,
             "energy_min":float(np.min(E_total)),
             "energy_max":float(np.max(E_total))},
  "classification":verdict,
  "files":{"scale_plot":"FAEV_G3RC3_ScaleFactor.png",
           "curvature_plot":"FAEV_G3RC3_Curvature.png",
           "mass_plot":"FAEV_G3RC3_Mass.png",
           "energy_plot":"FAEV_G3RC3_Energy.png"},
  "timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
out="backend/modules/knowledge/G3RC3_open_energy_feedback.json"
with open(out,"w") as f: json.dump(data,f,indent=2)

print("=== G3-RC3 - Open Energy Feedback (Soft-Capped Bounce) ===")
print(f"a_min={a_min:.4f} | cross_corr={cross_corr:.3f} | E_stab={E_stab:.3e}")
print(f"-> {verdict}")
print(f"✅ Results saved -> {out}")