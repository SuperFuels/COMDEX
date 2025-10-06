import json, os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from backend.photon_algebra.utils.load_constants import load_constants

# --- constants ---
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- setup ---
np.random.seed(42)
steps = 700
feedback_gain = 0.18
delay_steps = 8
noise_scale = 0.01
phase_shift = 0.07

# initial arrays
S_sys = [0.72]
S_obs = [0.70]
S_pred = [0.71]

for t in range(1, steps):
    noise = np.random.normal(0, noise_scale)
    
    delayed_index = max(0, t - delay_steps)
    delayed_feedback = S_obs[delayed_index]
    
    # system evolves under delayed observer influence
    dS_sys = -feedback_gain * (S_sys[-1] - delayed_feedback) + noise
    S_sys.append(S_sys[-1] + dS_sys * 0.002)
    
    # observer perceives system with phase lag
    phase_term = np.sin(2 * np.pi * phase_shift * t)
    dS_obs = feedback_gain * (S_sys[-1] - S_obs[-1]) + 0.5 * phase_term * noise
    S_obs.append(S_obs[-1] + dS_obs * 0.002)
    
    # predictive mirror (optional)
    S_pred.append(S_sys[-1] + np.sin(phase_term) * 0.001)

# convert
S_sys, S_obs, S_pred = map(np.array, (S_sys, S_obs, S_pred))

# --- metrics ---
corr = np.corrcoef(S_sys, S_obs)[0,1]
mean_drift = np.mean(np.gradient(S_sys - S_obs)[-100:])

if abs(mean_drift) < 1e-4 and corr > 0.95:
    cls = "✅ Stable temporal coupling"
elif abs(mean_drift) < 5e-4:
    cls = "⚠️ Phase drift"
else:
    cls = "❌ Causal inversion"

# --- plotting ---
plt.figure(figsize=(9,5))
plt.plot(S_sys, label="S_system")
plt.plot(S_obs, label="S_observer")
plt.plot(S_pred, label="S_pred (mirror)")
plt.title("O9 — Temporal Causality Feedback")
plt.xlabel("time step")
plt.ylabel("Entropy / coupling")
plt.legend()
plt.tight_layout()
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.savefig("PAEV_O9_TemporalFeedback.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "delay_steps": delay_steps,
    "noise_scale": noise_scale,
    "phase_shift": phase_shift,
    "mean_drift": float(mean_drift),
    "corr": float(corr),
    "classification": cls,
    "files": {"plot": "PAEV_O9_TemporalFeedback.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/O9_temporal_feedback.json","w") as f:
    json.dump(summary, f, indent=2)

print("=== O9 — Temporal Causality Feedback ===")
print(f"⟨ΔS⟩={mean_drift:.3e} | Corr={corr:.3f} | {cls}")
print("✅ Results saved → backend/modules/knowledge/O9_temporal_feedback.json")