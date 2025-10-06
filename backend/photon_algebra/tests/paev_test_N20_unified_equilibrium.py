import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ0, α0, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

np.random.seed(7)
t = np.linspace(0, 20, 2000)
dt = t[1]-t[0]
x = np.linspace(-5,5,600)
dx = x[1]-x[0]

# base state
psi = np.exp(-x**2) * np.exp(1j*0.2*x)

# knobs: time-varying α(t), Λ(t), thermal effective noise, and feedback
def alpha_t(tt):   return α0*(1+0.18*np.sin(0.35*tt))
def Lambda_t(tt):  return Λ0*(1+0.10*np.cos(0.27*tt))
T_eff = 3.6e18
kB = 8.617333262145e-5  # eV/K (scale proxy)
noise_scale = (kB*T_eff)*1e-21  # tiny, purely as simulation proxy

feedback_gain = 0.28  # from N13/N15 scales

psi_t = np.zeros((len(t), len(x)), dtype=complex)
psi_t[0] = psi.copy()

# simple evolution proxy: phase drift + curvature-like focusing + feedback stabilization
for i in range(1, len(t)):
    a = alpha_t(t[i])
    L = Lambda_t(t[i])
    phase = 0.15*a*dt*np.tanh(x) - 0.10*L*dt*x
    # focusing/defocusing term (curvature proxy)
    focusing = np.exp(-(0.02*a-0.015*L)*dt*x**2)
    # feedback towards first frame coherence (like lock-in)
    fb = feedback_gain*dt*(psi_t[0] - psi_t[i-1])
    # thermal noise (very small)
    nre = np.random.normal(scale=noise_scale, size=x.size)
    nim = np.random.normal(scale=noise_scale, size=x.size)
    noise = nre + 1j*nim

    psi_t[i] = (psi_t[i-1]*focusing*np.exp(1j*phase)) + fb + noise

# metrics
def entropy_proxy(v):
    p = np.abs(v)**2
    p = p/np.trapz(p, x)
    p = np.clip(p, 1e-18, None)
    return -np.trapz(p*np.log(p), x)

S = np.array([entropy_proxy(psi_t[i]) for i in range(len(t))])
dSdt = np.gradient(S, dt)

# equilibrium tests
S_tail_mean = np.mean(S[-200:])
dS_tail_mean = np.mean(dSdt[-200:])
coh = np.abs(np.trapz(np.conj(psi_t[0])*psi_t[-1], x))
coh /= np.sqrt(np.trapz(np.abs(psi_t[0])**2, x)*np.trapz(np.abs(psi_t[-1])**2, x))

if (abs(dS_tail_mean) < 5e-3) and (coh > 0.9):
    cls = "✅ Unified equilibrium reached"
elif (abs(dS_tail_mean) < 1e-2) and (coh > 0.75):
    cls = "⚠️ Near-equilibrium (quasi-steady)"
else:
    cls = "❌ Non-equilibrium"

# plots
os.makedirs("backend/modules/knowledge", exist_ok=True)

plt.figure(figsize=(9,5))
plt.plot(t, S)
plt.axhline(S_tail_mean, ls="--", alpha=0.6, label="⟨S⟩ tail")
plt.title("N20 — Entropy S(t)"); plt.xlabel("time"); plt.ylabel("S"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_N20_Entropy.png", dpi=120)

plt.figure(figsize=(9,5))
plt.plot(t, dSdt)
plt.axhline(0, color="k", lw=0.7, alpha=0.5)
plt.title("N20 — Entropy Flow dS/dt"); plt.xlabel("time"); plt.ylabel("dS/dt"); plt.tight_layout()
plt.savefig("PAEV_N20_EntropyFlow.png", dpi=120)

plt.figure(figsize=(9,5))
plt.plot(x, np.real(psi_t[0]), label="Re[ψ(0)]")
plt.plot(x, np.real(psi_t[-1]), "--", label="Re[ψ(final)]")
plt.title(f"N20 — Coherence final vs initial • |⟨ψ0|ψf⟩|={coh:.3f}")
plt.xlabel("x"); plt.ylabel("Re[ψ]"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_N20_Coherence.png", dpi=120)

# save summary
summary = {
    "ħ": ħ, "G": G, "Λ0": Λ0, "α0": α0, "β": β,
    "feedback_gain": feedback_gain,
    "T_eff": T_eff, "noise_scale_proxy": noise_scale,
    "S_tail_mean": float(S_tail_mean),
    "dSdt_tail_mean": float(dS_tail_mean),
    "final_coherence": float(coh),
    "classification": cls,
    "files": {
        "entropy": "PAEV_N20_Entropy.png",
        "flow": "PAEV_N20_EntropyFlow.png",
        "coherence": "PAEV_N20_Coherence.png",
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}
with open("backend/modules/knowledge/N20_unified_equilibrium.json","w") as f:
    json.dump(summary, f, indent=2)

print("=== N20 — Unified Equilibrium ===")
print(f"S_tail={S_tail_mean:.3f} • dS/dt_tail={dS_tail_mean:.3e} • coherence={coh:.3f}")
print(f"Classification: {cls}")
print("✅ Plots saved and results recorded → backend/modules/knowledge/N20_unified_equilibrium.json")