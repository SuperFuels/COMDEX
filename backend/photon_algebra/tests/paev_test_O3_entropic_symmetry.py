import json, os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- setup ---
np.random.seed(42)
steps = 600
x = np.linspace(-5, 5, 400)
dx = x[1] - x[0]

coupling = 0.28
noise_scale = 0.015

# initial gaussian waveforms
psi_sys = np.exp(-x**2)
psi_obs = np.exp(-1.2*x**2) * np.exp(1j*0.1*x)

# normalize
psi_sys /= np.sqrt(np.trapz(np.abs(psi_sys)**2, x))
psi_obs /= np.sqrt(np.trapz(np.abs(psi_obs)**2, x))

# --- simulate coupled evolution ---
S_sys, S_obs, I_mut = [], [], []
for t in range(steps):
    # evolve with mild asymmetry
    phase_shift = np.exp(1j * coupling * t / steps)
    psi_sys = psi_sys * phase_shift + noise_scale * (np.random.randn(len(x)) + 1j*np.random.randn(len(x)))
    psi_obs = psi_obs * np.conj(phase_shift) + noise_scale * (np.random.randn(len(x)) + 1j*np.random.randn(len(x)))

    # normalize each step
    psi_sys /= np.sqrt(np.trapz(np.abs(psi_sys)**2, x))
    psi_obs /= np.sqrt(np.trapz(np.abs(psi_obs)**2, x))

    # compute marginal entropies
    p_sys = np.abs(psi_sys)**2
    p_obs = np.abs(psi_obs)**2

    p_sys /= np.trapz(p_sys, x)
    p_obs /= np.trapz(p_obs, x)

    S_sys.append(-np.trapz(p_sys * np.log(p_sys + 1e-12), x))
    S_obs.append(-np.trapz(p_obs * np.log(p_obs + 1e-12), x))
    I_mut.append(np.trapz(np.sqrt(p_sys * p_obs), x))

# --- metrics ---
dSdt = np.gradient(S_sys)
mean_dSdt = np.mean(dSdt[-100:])

dIdt = np.gradient(I_mut)
mean_dIdt = np.mean(dIdt[-100:])

# --- classification ---
if mean_dSdt > 1e-4 and mean_dIdt < 0:
    cls = "🔥 Symmetry broken (forward flow)"
elif abs(mean_dSdt) < 5e-5:
    cls = "⚖️ Neutral (balanced)"
else:
    cls = "🌀 Overcoupled / oscillatory"

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(8,5))
plt.plot(S_sys, label="S_system")
plt.plot(S_obs, label="S_observer")
plt.plot(I_mut, label="Mutual Info")
plt.xlabel("time step"); plt.ylabel("Entropy / Info")
plt.title("O3 — Entropic Symmetry Break")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O3_EntropySymmetry.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "coupling": coupling,
    "noise_scale": noise_scale,
    "mean_dSdt_tail": float(mean_dSdt),
    "mean_dIdt_tail": float(mean_dIdt),
    "classification": cls,
    "files": {"plot": "PAEV_O3_EntropySymmetry.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/O3_entropic_symmetry.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== O3 — Entropic Symmetry Break ===")
print(f"⟨dS/dt⟩={mean_dSdt:.3e}, ⟨dI/dt⟩={mean_dIdt:.3e} • {cls}")
print("✅ Results saved → backend/modules/knowledge/O3_entropic_symmetry.json")