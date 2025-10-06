import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- simulation setup ---
np.random.seed(42)
x = np.linspace(-5, 5, 600)
dx = x[1] - x[0]

# Initial system and observer wavefunctions
psi_sys = np.exp(-x**2) * np.exp(1j * 0.3 * x)
psi_obs = np.exp(-0.8 * x**2) * np.exp(1j * 0.25 * x)

# Normalize
psi_sys /= np.sqrt(np.trapezoid(np.abs(psi_sys)**2, x))
psi_obs /= np.sqrt(np.trapezoid(np.abs(psi_obs)**2, x))

# Coupling constants
coupling_strength = 0.25
noise_scale = 0.01

timesteps = 400
ent_fid, I_mut, S_sys, S_obs = [], [], [], []

# --- dynamics loop ---
for t in range(timesteps):
    # stochastic coupling phase
    phase_shift = np.exp(1j * coupling_strength * np.sin(0.02 * t) + 1j * np.random.normal(0, noise_scale, len(x)))
    
    psi_sys = psi_sys * phase_shift
    psi_obs = psi_obs * np.conj(phase_shift)
    
    # normalize again
    psi_sys /= np.sqrt(np.trapezoid(np.abs(psi_sys)**2, x))
    psi_obs /= np.sqrt(np.trapezoid(np.abs(psi_obs)**2, x))
    
    # compute metrics
    overlap = np.trapezoid(np.conj(psi_sys) * psi_obs, x)
    F = np.abs(overlap)**2
    ent_fid.append(F)
    
    p_sys = np.abs(psi_sys)**2
    p_obs = np.abs(psi_obs)**2
    p_sys /= np.trapezoid(p_sys, x)
    p_obs /= np.trapezoid(p_obs, x)
    
    S_sys.append(-np.trapezoid(p_sys * np.log(p_sys + 1e-12), x))
    S_obs.append(-np.trapezoid(p_obs * np.log(p_obs + 1e-12), x))
    I_mut.append(np.trapezoid(np.sqrt(p_sys * p_obs), x))

# --- results ---
F_final = np.mean(ent_fid[-50:])
I_final = np.mean(I_mut[-50:])
dSdt = np.gradient(S_sys)[-10:].mean()

if F_final > 0.95 and abs(dSdt) < 1e-4:
    cls = "✅ Locked equilibrium"
elif F_final > 0.85:
    cls = "⚠️ Metastable coupling"
else:
    cls = "❌ Unlocked / decoherent"

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9,5))
plt.plot(ent_fid, label="Entanglement Fidelity")
plt.plot(I_mut, label="Mutual Information", alpha=0.7)
plt.title("O4 — Entanglement Lock Evolution")
plt.xlabel("time step"); plt.ylabel("Fidelity / Information")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O4_EntanglementLock.png", dpi=120)

# --- summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "coupling_strength": coupling_strength,
    "noise_scale": noise_scale,
    "final_entanglement_fidelity": F_final,
    "final_mutual_info": I_final,
    "mean_dSdt_tail": float(dSdt),
    "classification": cls,
    "files": {"plot": "PAEV_O4_EntanglementLock.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/O4_entanglement_lock.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== O4 — Observer Entanglement Lock ===")
print(f"F_final={F_final:.3f}, I_final={I_final:.3f}, dS/dt={dSdt:.2e} → {cls}")
print("✅ Results saved → backend/modules/knowledge/O4_entanglement_lock.json")