import json, os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from backend.photon_algebra.utils.load_constants import load_constants

# --- Load constants ---
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- Parameters ---
np.random.seed(42)
steps = 600
learning_rate = 0.05
feedback_gain = 0.2
noise_scale = 0.008

# --- Initial conditions ---
S_sys = [0.72]
S_obs = [0.70]
S_pred = [0.71]
error_trace = []

# --- Predictive evolution ---
for t in range(1, steps):
    noise = np.random.normal(0, noise_scale)
    # system evolution
    dS_sys = -feedback_gain * (S_sys[-1] - S_obs[-1]) + noise
    S_sys.append(S_sys[-1] + dS_sys)
    
    # observer tracking
    dS_obs = feedback_gain * (S_sys[-2] - S_obs[-1]) + 0.5 * noise
    S_obs.append(S_obs[-1] + dS_obs)
    
    # predictor estimates next system state
    S_pred_next = S_pred[-1] + learning_rate * (S_sys[-1] - S_pred[-1])
    S_pred.append(S_pred_next)
    
    # prediction error
    error = S_sys[-1] - S_pred_next
    error_trace.append(error)

# --- Metrics ---
error_trace = np.array(error_trace)
mean_error = np.mean(np.abs(error_trace[-100:]))
corr_pred = np.corrcoef(S_sys[-len(S_pred):], S_pred)[0,1]
stability = np.std(error_trace[-100:])

# --- Classification ---
if mean_error < 1e-3 and corr_pred > 0.98:
    cls = "✅ Predictively locked"
elif mean_error < 5e-3:
    cls = "⚠️ Partial self-prediction"
else:
    cls = "❌ Non-predictive regime"

# --- Plot ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9,5))
plt.plot(S_sys, label="S_system")
plt.plot(S_obs, label="S_observer")
plt.plot(S_pred, label="S_pred (forecast)")
plt.title("P1 - Predictive Observer Calibration")
plt.xlabel("time step")
plt.ylabel("Entropy")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P1_PredictiveCalibration.png", dpi=120)

plt.figure(figsize=(9,4))
plt.plot(error_trace, label="Prediction Error ΔS_pred")
plt.title("P1 - Prediction Error Evolution")
plt.xlabel("time step")
plt.ylabel("ΔS_pred")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P1_PredictionError.png", dpi=120)

# --- Save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "learning_rate": learning_rate,
    "feedback_gain": feedback_gain,
    "noise_scale": noise_scale,
    "mean_error": float(mean_error),
    "corr_prediction": float(corr_pred),
    "stability": float(stability),
    "classification": cls,
    "files": {
        "entropy_plot": "PAEV_P1_PredictiveCalibration.png",
        "error_plot": "PAEV_P1_PredictionError.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P1_predictive_calibration.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== P1 - Predictive Observer Calibration ===")
print(f"⟨|ΔS_pred|⟩={mean_error:.3e} | Corr={corr_pred:.3f} | {cls}")
print("✅ Results saved -> backend/modules/knowledge/P1_predictive_calibration.json")