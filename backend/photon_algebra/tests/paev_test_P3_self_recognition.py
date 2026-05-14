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
steps = 700
learning_rate = 0.05
feedback_gain = 0.18
meta_gain = 0.12
recognition_gain = 0.07
noise_scale = 0.007

# --- initial conditions ---
S_system = [0.72]
S_observer = [0.70]
S_meta = [0.68]
S_self = [0.67]   # self-recognition entropy channel

# --- evolution ---
for t in range(1, steps):
    noise = np.random.normal(0, noise_scale)

    # Observer reacts to system
    dS_obs = feedback_gain * (S_system[-1] - S_observer[-1]) + noise

    # Meta reacts to observer
    dS_meta = meta_gain * (S_observer[-1] - S_meta[-1]) + 0.5 * noise

    # Self-recognition reacts to meta-layer with self-reinforcing correction
    dS_self = recognition_gain * (S_meta[-1] - S_self[-1]) + 0.5 * np.sign(S_meta[-1] - S_self[-1]) * noise

    # System experiences small drift from observer feedback
    dS_sys = -0.5 * feedback_gain * (S_observer[-1] - S_meta[-1])

    S_system.append(S_system[-1] + dS_sys)
    S_observer.append(S_observer[-1] + dS_obs)
    S_meta.append(S_meta[-1] + dS_meta)
    S_self.append(S_self[-1] + dS_self)

# --- convert arrays ---
S_system, S_observer, S_meta, S_self = map(np.array, [S_system, S_observer, S_meta, S_self])

# --- metrics ---
meta_overlap = np.corrcoef(S_meta, S_self)[0, 1]
recognition_stability = np.mean(np.abs(np.gradient(S_self - S_meta)))
mean_drift = np.mean(np.gradient(S_self))

# --- classification ---
if meta_overlap > 0.95 and recognition_stability < 0.005:
    cls = "✅ Stable self-recognition achieved"
elif meta_overlap > 0.85:
    cls = "⚠️ Latent self-recognition"
else:
    cls = "❌ No self-recognition"

# --- plotting ---
plt.figure(figsize=(9,5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_meta, label="S_meta (awareness)")
plt.plot(S_self, label="S_self (recognition)")
plt.title("P3 - Meta-Stable Self-Recognition")
plt.xlabel("time step")
plt.ylabel("Entropy")
plt.legend()
plt.tight_layout()

os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.savefig("PAEV_P3_SelfRecognition.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "learning_rate": learning_rate,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "recognition_gain": recognition_gain,
    "noise_scale": noise_scale,
    "meta_overlap": float(meta_overlap),
    "recognition_stability": float(recognition_stability),
    "mean_drift": float(mean_drift),
    "classification": cls,
    "files": {"plot": "PAEV_P3_SelfRecognition.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/P3_self_recognition.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== P3 - Meta-Stable Self-Recognition ===")
print(f"Overlap={meta_overlap:.3f} | Stability={recognition_stability:.3e} | Drift={mean_drift:.3e} | {cls}")
print("✅ Results saved -> backend/modules/knowledge/P3_self_recognition.json")