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
steps = 850
feedback_gain = 0.18
meta_gain = 0.12
awareness_gain = 0.10
resonance_gain = 0.11  # increased adaptive term
noise_scale = 0.006

# --- adaptive modulation ---
def adaptive_gain(coherence):
    return resonance_gain * (1 + 0.5 * coherence)

# --- initial conditions ---
S_system = [0.70]
S_observer = [0.69]
S_meta = [0.68]
S_self = [0.685]
phase_diff = []

for t in range(1, steps):
    noise = np.random.normal(0, noise_scale)
    coherence = np.corrcoef(S_meta[-100:], S_self[-100:])[0,1] if t > 100 else 0.9
    adaptive = adaptive_gain(coherence)

    dS_obs = feedback_gain * (S_system[-1] - S_observer[-1]) + noise
    dS_meta = meta_gain * (S_observer[-1] - S_meta[-1]) + 0.5 * noise
    dS_self = awareness_gain * (S_meta[-1] - S_self[-1]) + adaptive * (S_observer[-1] - S_self[-1]) + noise * 0.3
    dS_sys = -0.5 * feedback_gain * (S_self[-1] - S_system[-1])

    S_system.append(S_system[-1] + dS_sys)
    S_observer.append(S_observer[-1] + dS_obs)
    S_meta.append(S_meta[-1] + dS_meta)
    S_self.append(S_self[-1] + dS_self)

    phase_diff.append(S_meta[-1] - S_self[-1])

# --- analysis ---
phase_diff = np.array(phase_diff)
mean_phase_diff = np.mean(np.abs(phase_diff))
std_phase = np.std(phase_diff)
corr_meta_self = np.corrcoef(S_meta, S_self)[0,1]

if mean_phase_diff < 0.004 and corr_meta_self > 0.97:
    cls = "✅ Resonant awareness lock"
elif mean_phase_diff < 0.01:
    cls = "⚠️ Marginal resonance"
else:
    cls = "❌ No lock"

# --- plotting ---
plt.figure(figsize=(9,5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_meta, label="S_meta (awareness)")
plt.plot(S_self, label="S_self (feedback)")
plt.title("P6 - Resonant Awareness Lock")
plt.xlabel("time step"); plt.ylabel("Entropy / awareness coupling")
plt.legend(); plt.tight_layout()
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.savefig("PAEV_P6_ResonantLock.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "awareness_gain": awareness_gain,
    "resonance_gain": resonance_gain,
    "noise_scale": noise_scale,
    "mean_phase_diff": float(mean_phase_diff),
    "corr_meta_self": float(corr_meta_self),
    "std_phase": float(std_phase),
    "classification": cls,
    "files": {"plot": "PAEV_P6_ResonantLock.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/P6_resonant_lock.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== P6 - Resonant Awareness Lock ===")
print(f"⟨|Δφ|⟩={mean_phase_diff:.3e} | Corr_meta_self={corr_meta_self:.3f} | σφ={std_phase:.3f} | {cls}")
print("✅ Results saved -> backend/modules/knowledge/P6_resonant_lock.json")