import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

np.random.seed(42)
x = np.linspace(-5, 5, 600)

# initial states
psi_sys = np.exp(-x**2) * np.exp(1j*0.30*x)
psi_obs = np.exp(-0.8*x**2) * np.exp(1j*0.25*x)

def norm(ψ):
    return ψ/np.sqrt(np.trapezoid(np.abs(ψ)**2, x))

psi_sys = norm(psi_sys)
psi_obs = norm(psi_obs)

# --- params (tuned for lock) ---
coupling_strength = 0.18           # slightly weaker than O4
noise_scale       = 0.006           # less stochastic spread
lock_gain         = 0.06            # phase servo gain (0.03-0.08 works)
avg_gain          = 0.02            # slow drift cancellation on amplitudes
timesteps         = 500

ent_fid, I_mut, S_sys, S_obs, phi_hat_series = [], [], [], [], []

def entropy(ψ):
    p = np.abs(ψ)**2
    p /= np.trapezoid(p, x)
    return -np.trapezoid(p*np.log(p+1e-12), x), p

for t in range(timesteps):
    # 1) forward stochastic coupling (what dephases us)
    phase_noise = np.random.normal(0, noise_scale, len(x))
    phase_drive = coupling_strength*np.sin(0.02*t)
    phase = np.exp(1j*(phase_drive + phase_noise))
    psi_sys = psi_sys*phase
    psi_obs = psi_obs*np.conj(phase)
    
    # 2) estimate relative phase and servo-correct the observer
    overlap = np.trapezoid(np.conj(psi_sys)*psi_obs, x)
    phi_hat = np.angle(overlap)            # how far off we are
    psi_obs *= np.exp(-1j*lock_gain*phi_hat)  # small corrective rotation
    phi_hat_series.append(phi_hat)
    
    # 3) very gentle amplitude equalization to prevent slow drift
    S_s, p_s = entropy(psi_sys)
    S_o, p_o = entropy(psi_obs)
    amp_err = np.sign(np.mean(p_s - p_o))
    psi_obs *= np.exp(-avg_gain*amp_err)   # tiny bias toward matching spread
    
    # normalize after corrections
    psi_sys = norm(psi_sys); psi_obs = norm(psi_obs)
    
    # metrics
    F = np.abs(overlap)**2
    ent_fid.append(F)
    S_sys.append(S_s); S_obs.append(S_o)
    I_mut.append(np.trapezoid(np.sqrt(p_s*p_o), x))

# tails
F_final  = float(np.mean(ent_fid[-50:]))
I_final  = float(np.mean(I_mut[-50:]))
dSdt     = float(np.gradient(S_sys)[-20:].mean())

if F_final > 0.95 and abs(dSdt) < 1e-4:
    cls = "✅ Locked equilibrium"
elif F_final > 0.88:
    cls = "⚠️ Metastable coupling"
else:
    cls = "❌ Unlocked / decoherent"

# plots
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9,5))
plt.plot(ent_fid, label="Entanglement Fidelity")
plt.plot(I_mut,  label="Mutual Information", alpha=0.8)
plt.title("O4a - Adaptive Entanglement Lock (phase servo)")
plt.xlabel("time step"); plt.ylabel("Fidelity / Information")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O4a_EntanglementLock.png", dpi=120)

plt.figure(figsize=(9,4))
plt.plot(phi_hat_series)
plt.title("O4a - Estimated Phase Error φ̂ (per step)")
plt.xlabel("time step"); plt.ylabel("radians")
plt.tight_layout()
plt.savefig("PAEV_O4a_PhaseError.png", dpi=120)

# save
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "coupling_strength": coupling_strength,
    "noise_scale": noise_scale,
    "lock_gain": lock_gain,
    "avg_gain": avg_gain,
    "final_entanglement_fidelity": F_final,
    "final_mutual_info": I_final,
    "mean_dSdt_tail": dSdt,
    "classification": cls,
    "files": {
        "lock_plot": "PAEV_O4a_EntanglementLock.png",
        "phase_plot": "PAEV_O4a_PhaseError.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}
with open("backend/modules/knowledge/O4a_entanglement_lock_adaptive.json","w") as f:
    json.dump(summary, f, indent=2)

print("=== O4a - Adaptive Entanglement Lock ===")
print(f"F_final={F_final:.3f}, I_final={I_final:.3f}, dS/dt={dSdt:.2e} -> {cls}")
print("✅ Results saved -> backend/modules/knowledge/O4a_entanglement_lock_adaptive.json")