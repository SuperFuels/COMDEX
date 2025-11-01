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
x = np.linspace(-4, 4, 400)
S_sys, S_obs, F_feedback = [], [], []

# initial conditions
S_sys_val, S_obs_val = 0.72, 0.70
feedback_gain = 0.18
noise_scale = 0.01

for t in range(steps):
    # entropy drift with mild coupling and noise
    dS = -feedback_gain * (S_sys_val - S_obs_val) + np.random.normal(0, noise_scale)
    S_sys_val += dS * 0.002
    S_obs_val += -dS * 0.0025  # observer counter-adjusts
    
    # feedback correlation proxy
    F_feedback.append(-dS * feedback_gain)
    S_sys.append(S_sys_val)
    S_obs.append(S_obs_val)

# --- metrics ---
S_sys, S_obs, F_feedback = np.array(S_sys), np.array(S_obs), np.array(F_feedback)
dSdt = np.gradient(S_sys)
corr = np.corrcoef(S_sys, S_obs)[0,1]
mean_drift = np.mean(dSdt[-100:])
mean_feedback = np.mean(F_feedback[-100:])

# classification
if abs(mean_drift) < 1e-4 and corr > 0.9:
    cls = "✅ Balanced feedback equilibrium"
elif abs(mean_drift) < 5e-4:
    cls = "⚠️ Under-coupled feedback"
else:
    cls = "❌ Unstable feedback loop"

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9,5))
plt.plot(S_sys, label="S_system")
plt.plot(S_obs, label="S_observer")
plt.title("O6 - Observer Feedback Entropy Loop")
plt.xlabel("time step")
plt.ylabel("Entropy")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_O6_FeedbackEntropy.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "noise_scale": noise_scale,
    "mean_drift": float(mean_drift),
    "feedback_correlation": float(corr),
    "mean_feedback": float(mean_feedback),
    "classification": cls,
    "files": {"plot": "PAEV_O6_FeedbackEntropy.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/O6_feedback_entropy.json","w") as f:
    json.dump(summary, f, indent=2)

print("=== O6 - Observer Feedback Entropy Loop ===")
print(f"⟨dS/dt⟩={mean_drift:.3e} | Corr={corr:.3f} | {cls}")
print("✅ Results saved -> backend/modules/knowledge/O6_feedback_entropy.json")