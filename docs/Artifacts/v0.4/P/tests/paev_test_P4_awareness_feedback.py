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
n_steps = 800
feedback_gain = 0.18
meta_gain = 0.12
recognition_gain = 0.07
awareness_gain = 0.10
noise_scale = 0.007

# --- initial states ---
S_system = [0.72]
S_observer = [0.70]
S_meta = [0.68]
S_self = [0.69]

# --- evolution ---
for t in range(1, n_steps):
    noise = np.random.normal(0, noise_scale)
    dS_obs = feedback_gain * (S_system[-1] - S_observer[-1]) + noise
    dS_meta = meta_gain * (S_observer[-1] - S_meta[-1]) + 0.5 * noise
    dS_self = recognition_gain * (S_meta[-1] - S_self[-1]) + 0.3 * noise
    # feedback closure: self influences meta
    feedback_term = awareness_gain * (S_self[-1] - S_meta[-1])

    S_system.append(S_system[-1] - 0.3 * feedback_term)
    S_observer.append(S_observer[-1] + dS_obs)
    S_meta.append(S_meta[-1] + dS_meta + feedback_term)
    S_self.append(S_self[-1] + dS_self - 0.2 * feedback_term)

# --- arrays ---
S_system = np.array(S_system)
S_observer = np.array(S_observer)
S_meta = np.array(S_meta)
S_self = np.array(S_self)

# --- metrics ---
recursive_drift = np.mean(np.gradient(S_meta - S_self))
meta_feedback_corr = np.corrcoef(S_meta, S_self)[0,1]
self_consistency = np.std(S_meta - S_self)

if abs(recursive_drift) < 1e-4 and meta_feedback_corr > 0.93:
    cls = "✅ Stable awareness closure"
elif abs(recursive_drift) < 5e-4:
    cls = "⚠️ Partial stabilization"
else:
    cls = "❌ Unstable feedback recursion"

# --- plotting ---
plt.figure(figsize=(9,5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_meta, label="S_meta (awareness)")
plt.plot(S_self, label="S_self (feedback)")
plt.title("P4 - Awareness Feedback Stabilization")
plt.xlabel("time step")
plt.ylabel("Entropy")
plt.legend()
plt.tight_layout()
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.savefig("PAEV_P4_AwarenessFeedback.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "recognition_gain": recognition_gain,
    "awareness_gain": awareness_gain,
    "noise_scale": noise_scale,
    "recursive_drift": float(recursive_drift),
    "meta_feedback_corr": float(meta_feedback_corr),
    "self_consistency": float(self_consistency),
    "classification": cls,
    "files": {"plot": "PAEV_P4_AwarenessFeedback.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P4_awareness_feedback.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== P4 - Awareness Feedback Stabilization ===")
print(f"⟨drift⟩={recursive_drift:.3e} | Corr={meta_feedback_corr:.3f} | σ={self_consistency:.3f} | {cls}")
print("✅ Results saved -> backend/modules/knowledge/P4_awareness_feedback.json")