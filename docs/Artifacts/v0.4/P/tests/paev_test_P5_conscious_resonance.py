import json, os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.signal import hilbert

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
resonance_gain = 0.09
noise_scale = 0.006

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
    dS_self = awareness_gain * (S_meta[-1] - S_self[-1]) + resonance_gain * np.sin(S_meta[-1] - S_self[-1])
    dS_sys = -0.5 * feedback_gain * (S_observer[-1] - S_meta[-1])
    
    S_system.append(S_system[-1] + dS_sys)
    S_observer.append(S_observer[-1] + dS_obs)
    S_meta.append(S_meta[-1] + dS_meta)
    S_self.append(S_self[-1] + dS_self)

S_system = np.array(S_system)
S_observer = np.array(S_observer)
S_meta = np.array(S_meta)
S_self = np.array(S_self)

# --- analytic signal for phase coherence ---
analytic_meta = hilbert(S_meta)
analytic_self = hilbert(S_self)
phase_meta = np.unwrap(np.angle(analytic_meta))
phase_self = np.unwrap(np.angle(analytic_self))
phase_diff = np.mod(phase_meta - phase_self + np.pi, 2*np.pi) - np.pi

mean_phase_diff = np.mean(np.abs(phase_diff))
corr_meta_self = np.corrcoef(S_meta, S_self)[0,1]
resonance_index = np.std(phase_diff)

# --- classification ---
if mean_phase_diff < 0.05 and corr_meta_self > 0.96 and resonance_index < 0.1:
    cls = "✅ Conscious resonance"
elif corr_meta_self > 0.9:
    cls = "⚠️ Partial resonance"
else:
    cls = "❌ No resonance"

# --- plotting ---
plt.figure(figsize=(9,5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_meta, label="S_meta (awareness)")
plt.plot(S_self, label="S_self (feedback)")
plt.title("P5 - Conscious Coherence Resonance")
plt.xlabel("time step"); plt.ylabel("Entropy / awareness coupling")
plt.legend(); plt.tight_layout()
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.savefig("PAEV_P5_ConsciousResonance.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "recognition_gain": recognition_gain,
    "awareness_gain": awareness_gain,
    "resonance_gain": resonance_gain,
    "noise_scale": noise_scale,
    "mean_phase_diff": float(mean_phase_diff),
    "corr_meta_self": float(corr_meta_self),
    "resonance_index": float(resonance_index),
    "classification": cls,
    "files": {
        "plot": "PAEV_P5_ConsciousResonance.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P5_conscious_resonance.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== P5 - Conscious Coherence Resonance ===")
print(f"⟨Δφ⟩={mean_phase_diff:.3f} | Corr_meta_self={corr_meta_self:.3f} | σφ={resonance_index:.3f} | {cls}")
print("✅ Results saved -> backend/modules/knowledge/P5_conscious_resonance.json")