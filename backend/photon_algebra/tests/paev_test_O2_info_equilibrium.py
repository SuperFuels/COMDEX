import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- Load global constants from registry ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- Parameters ---
np.random.seed(42)
steps = 500
coupling_strength = 0.25
noise_scale = 0.02

# --- Initialize fields (system and observer) ---
x = np.linspace(-4, 4, 400)
psi_sys = np.exp(-x**2) * np.exp(1j * 0.3 * x)
psi_obs = np.exp(-x**2) * np.exp(-1j * 0.3 * x)
dx = x[1] - x[0]

def normalize(psi):
    norm = np.sqrt(np.trapezoid(np.abs(psi)**2, x))
    return psi / norm

def entropy(psi):
    p = np.abs(psi)**2
    p = p / np.trapezoid(p, x)
    return -np.trapezoid(p * np.log(p + 1e-12), x)

def mutual_information(psi_a, psi_b):
    # overlap-based proxy for shared information
    overlap = np.abs(np.trapezoid(np.conj(psi_a) * psi_b, x))**2
    return overlap

# --- Evolution loop ---
S_sys, S_obs, I_mut = [], [], []
for t in range(steps):
    # system-observer coupling with weak stochastic exchange
    dpsi_sys = coupling_strength * (psi_obs - psi_sys) + noise_scale * (np.random.randn(len(x)) + 1j*np.random.randn(len(x)))
    dpsi_obs = coupling_strength * (psi_sys - psi_obs) + noise_scale * (np.random.randn(len(x)) + 1j*np.random.randn(len(x)))

    psi_sys += dpsi_sys * 1e-3
    psi_obs += dpsi_obs * 1e-3

    psi_sys = normalize(psi_sys)
    psi_obs = normalize(psi_obs)

    S_sys.append(entropy(psi_sys))
    S_obs.append(entropy(psi_obs))
    I_mut.append(mutual_information(psi_sys, psi_obs))

# --- Equilibrium analysis ---
S_total = np.array(S_sys) + np.array(S_obs) - np.array(I_mut)
dS_total = np.gradient(S_total)
mean_drift = np.mean(np.abs(dS_total[-50:]))

if mean_drift < 1e-3:
    cls = "✅ Balanced exchange"
elif mean_drift < 5e-3:
    cls = "⚠️ Partial drift"
else:
    cls = "❌ Unstable information flow"

# --- Plot ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9,5))
plt.plot(S_sys, label="S_system")
plt.plot(S_obs, label="S_observer")
plt.plot(I_mut, label="Mutual Info")
plt.title("O2 - Information Exchange Equilibrium")
plt.xlabel("time step")
plt.ylabel("Entropy / Information")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_O2_InfoEquilibrium.png", dpi=120)

# --- Save results ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "coupling_strength": coupling_strength,
    "noise_scale": noise_scale,
    "mean_drift": mean_drift,
    "final_S_sys": float(S_sys[-1]),
    "final_S_obs": float(S_obs[-1]),
    "final_I_mut": float(I_mut[-1]),
    "classification": cls,
    "files": {
        "plot": "PAEV_O2_InfoEquilibrium.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

out_path = "backend/modules/knowledge/O2_info_equilibrium.json"
with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)

print("=== O2 - Information Exchange Equilibrium ===")
print(f"Mean drift={mean_drift:.3e} -> {cls}")
print(f"✅ Results saved -> {out_path}")