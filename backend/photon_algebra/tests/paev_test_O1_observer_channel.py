import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- Load constants from registry ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- Parameters ---
np.random.seed(42)
x = np.linspace(-5, 5, 600)
dx = x[1] - x[0]
t_steps = 400
observer_gain = 0.15   # coupling between ψ and ψ_obs
noise_scale = 0.01

# --- Initialize system state ---
psi = np.exp(-x**2) * np.exp(1j*0.2*x)
psi_obs = np.zeros_like(psi, dtype=complex)

# --- Helper functions ---
def norm(a): return np.sqrt(np.trapezoid(np.abs(a)**2, x))
def fidelity(a, b): 
    return np.abs(np.trapezoid(np.conj(a)*b, x) / (norm(a)*norm(b)))

def entropy(p):
    p = np.abs(p)**2
    p /= np.trapezoid(p, x)
    return -np.trapezoid(p * np.log(p + 1e-12), x)

# --- Simulation loop ---
entropies_sys = []
entropies_obs = []
mutual_info = []
for t in range(t_steps):
    # System evolves (simple Schrödinger-type drift)
    psi = psi * np.exp(-1j * (ħ * x**2 + α*np.sin(x*t*1e-3)))

    # Observer reads part of ψ with coupling
    psi_obs += observer_gain * (psi - psi_obs) + noise_scale * (np.random.randn(len(x)) + 1j*np.random.randn(len(x))) * 1e-3

    # Record measures
    S_sys = entropy(psi)
    S_obs = entropy(psi_obs)
    S_joint = entropy(psi + psi_obs)
    mutual_info.append(S_sys + S_obs - S_joint)
    entropies_sys.append(S_sys)
    entropies_obs.append(S_obs)

# --- Final metrics ---
F_obs = fidelity(psi, psi_obs)
MI_mean = np.mean(mutual_info[-100:])
S_sys_tail = np.mean(entropies_sys[-100:])
S_obs_tail = np.mean(entropies_obs[-100:])

# --- Classification logic ---
if F_obs > 0.9 and MI_mean > 0.01:
    cls = "✅ Stable observer coupling"
elif F_obs > 0.5:
    cls = "⚠️ Weakly coupled / noisy observation"
else:
    cls = "❌ Decoherence-dominated"

# --- Plot results ---
os.makedirs("backend/modules/knowledge", exist_ok=True)

plt.figure(figsize=(9,5))
plt.plot(entropies_sys, label="S_system")
plt.plot(entropies_obs, label="S_observer")
plt.plot(mutual_info, label="Mutual Info")
plt.xlabel("time step")
plt.ylabel("Entropy / Information")
plt.title("O1 — Observer Channel Activation")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O1_ObserverChannel.png", dpi=120)

# --- Save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "observer_gain": observer_gain,
    "noise_scale": noise_scale,
    "final_fidelity": float(F_obs),
    "mean_mutual_info": float(MI_mean),
    "S_system_tail": float(S_sys_tail),
    "S_observer_tail": float(S_obs_tail),
    "classification": cls,
    "files": {"plot": "PAEV_O1_ObserverChannel.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}
with open("backend/modules/knowledge/O1_observer_channel.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== O1 — Observer Channel Activation ===")
print(f"Final Fidelity={F_obs:.3f} | ⟨MI⟩={MI_mean:.3e} | {cls}")
print("✅ Results saved → backend/modules/knowledge/O1_observer_channel.json")