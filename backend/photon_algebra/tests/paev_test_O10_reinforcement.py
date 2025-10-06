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
steps = 800
feedback_gain = 0.20
learning_rate = 0.05
noise_scale = 0.009
phase_shift = 0.06

# --- initialize states ---
S_sys = [0.72]
S_obs = [0.70]
S_pred = [0.71]
error_memory = [0.0]

for t in range(1, steps):
    noise = np.random.normal(0, noise_scale)
    
    # System entropy evolution (natural drift + coupling)
    dS_sys = -0.0008 * np.sin(0.02*t + phase_shift) + noise
    S_sys.append(S_sys[-1] + dS_sys)
    
    # Observer prediction (previous + learned correction)
    pred_error = (S_sys[-1] - S_pred[-1])
    S_pred.append(S_pred[-1] + feedback_gain * pred_error)
    
    # Observer adjusts its own bias recursively
    correction = learning_rate * pred_error
    S_obs.append(S_obs[-1] + correction + 0.5*noise)
    
    # Store running prediction error
    error_memory.append(pred_error)

# --- metrics ---
S_sys, S_obs, S_pred = np.array(S_sys), np.array(S_obs), np.array(S_pred)
error_memory = np.array(error_memory)

mean_error = np.mean(np.abs(error_memory[-200:]))
corr_pred = np.corrcoef(S_sys[-200:], S_pred[-200:])[0,1]
drift = np.mean(np.gradient(S_sys[-200:]))

# --- classification ---
if mean_error < 1e-3 and corr_pred > 0.98:
    cls = "✅ Self-correcting feedback stable"
elif mean_error < 5e-3:
    cls = "⚠️ Semi-adaptive regime"
else:
    cls = "❌ Divergent learning loop"

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)

plt.figure(figsize=(9,5))
plt.plot(S_sys, label="S_system")
plt.plot(S_obs, label="S_observer")
plt.plot(S_pred, label="S_pred (recursive)")
plt.title("O10 — Recursive Predictive Reinforcement")
plt.xlabel("time step"); plt.ylabel("Entropy")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O10_Reinforcement.png", dpi=120)

plt.figure(figsize=(9,5))
plt.plot(error_memory, label="Prediction Error")
plt.title("O10 — Recursive Prediction Error Evolution")
plt.xlabel("time step"); plt.ylabel("ΔS_pred")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O10_ReinforcementError.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "learning_rate": learning_rate,
    "noise_scale": noise_scale,
    "phase_shift": phase_shift,
    "mean_error": float(mean_error),
    "corr_prediction": float(corr_pred),
    "entropy_drift": float(drift),
    "classification": cls,
    "files": {
        "entropy_plot": "PAEV_O10_Reinforcement.png",
        "error_plot": "PAEV_O10_ReinforcementError.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/O10_reinforcement.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== O10 — Recursive Predictive Reinforcement ===")
print(f"⟨|ΔS_pred|⟩={mean_error:.3e} | Corr={corr_pred:.3f} | Drift={drift:.2e} → {cls}")
print("✅ Results saved → backend/modules/knowledge/O10_reinforcement.json")