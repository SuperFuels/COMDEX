import json, os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameters ---
np.random.seed(42)
n_steps = 700
feedback_gain = 0.20
predictive_gain = 0.15
noise_scale = 0.008
phase_lag = 0.05

# --- initialize state variables ---
S_system = [0.72]
S_observer = [0.70]
S_predict = [0.69]

pred_errors = []

for t in range(1, n_steps):
    # noise and drift
    noise = np.random.normal(0, noise_scale)
    
    # system evolves with mild entropy decay
    dS_sys = -0.0005 * (S_system[-1] - 0.7) + noise
    S_system.append(S_system[-1] + dS_sys)
    
    # observer attempts to track system with feedback
    dS_obs = feedback_gain * (S_system[-2] - S_observer[-1]) + 0.8 * noise
    S_observer.append(S_observer[-1] + dS_obs)
    
    # predictive model tries to forecast next system step
    prediction = S_observer[-1] + predictive_gain * (S_observer[-1] - S_predict[-1])
    S_predict.append(prediction)
    
    # measure prediction error (phase-adjusted)
    pred_error = (S_system[-1] - S_predict[-1]) * np.cos(phase_lag * t)
    pred_errors.append(pred_error)

# --- metrics ---
S_system = np.array(S_system)
S_predict = np.array(S_predict)
pred_errors = np.array(pred_errors)

error_mean = np.mean(np.abs(pred_errors[-200:]))
corr = np.corrcoef(S_system[-300:], S_predict[-300:])[0, 1]

# classification
if corr > 0.9 and error_mean < 1e-3:
    cls = "✅ Causally coherent"
elif corr > 0.7:
    cls = "⚠️ Partially predictive"
else:
    cls = "❌ Retrocausal drift"

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9,5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_predict, label="S_predict (forecast)")
plt.title("O8 — Causal Prediction Horizon")
plt.xlabel("time step"); plt.ylabel("Entropy")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O8_CausalPrediction.png", dpi=120)

plt.figure(figsize=(9,5))
plt.plot(pred_errors, label="Prediction Error (phase-adjusted)")
plt.title("O8 — Phase-Adjusted Prediction Error")
plt.xlabel("time step"); plt.ylabel("ΔS_pred")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_O8_PredictionError.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "predictive_gain": predictive_gain,
    "noise_scale": noise_scale,
    "phase_lag": phase_lag,
    "mean_error": float(error_mean),
    "corr_prediction": float(corr),
    "classification": cls,
    "files": {
        "entropy_plot": "PAEV_O8_CausalPrediction.png",
        "error_plot": "PAEV_O8_PredictionError.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/O8_causal_prediction.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== O8 — Causal Prediction Horizon ===")
print(f"⟨|ΔS_pred|⟩={error_mean:.3e} | Corr={corr:.3f} | {cls}")
print("✅ Results saved → backend/modules/knowledge/O8_causal_prediction.json")