import json, os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameters ---
np.random.seed(42)
n_steps = 600
feedback_gain = 0.22
meta_gain = 0.12
noise_scale = 0.008

# --- initial states ---
S_system = [0.72]
S_observer = [0.70]
S_meta = [0.68]

# --- evolution loop ---
for t in range(1, n_steps):
    noise = np.random.normal(0, noise_scale)
    
    # Observer responds to system–observer entropy difference
    dS_obs = feedback_gain * (S_system[-1] - S_observer[-1]) + noise
    
    # Meta-layer (recursive observer) follows observer entropy trend
    dS_meta = meta_gain * (S_observer[-1] - S_meta[-1]) + 0.5 * noise
    
    # System reacts slightly to the meta-observer
    dS_sys = -0.5 * feedback_gain * (S_observer[-1] - S_meta[-1])
    
    # Update all layers
    S_system.append(S_system[-1] + dS_sys)
    S_observer.append(S_observer[-1] + dS_obs)
    S_meta.append(S_meta[-1] + dS_meta)

# --- convert to numpy arrays ---
S_system = np.array(S_system)
S_observer = np.array(S_observer)
S_meta = np.array(S_meta)

# --- metrics ---
meta_drift = np.mean(np.gradient(S_meta))
corr_meta = np.corrcoef(S_meta, S_observer)[0, 1]

# --- classification ---
if abs(meta_drift) < 1e-4 and corr_meta > 0.9:
    cls = "✅ Stable self-observation"
elif abs(meta_drift) < 5e-4 and corr_meta > 0.8:
    cls = "⚠️ Marginal stability"
else:
    cls = "❌ Divergent recursion"

# --- plotting ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9, 5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_meta, label="S_meta (recursive)")
plt.title("O7 — Recursive Self-Observation Stability")
plt.xlabel("time step")
plt.ylabel("Entropy")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_O7_SelfObservation.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "noise_scale": noise_scale,
    "meta_drift": float(meta_drift),
    "corr_meta": float(corr_meta),
    "classification": cls,
    "files": {"plot": "PAEV_O7_SelfObservation.png"},
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/O7_self_observation.json", "w") as f:
    json.dump(summary, f, indent=2)

# --- output summary ---
print("=== O7 — Recursive Self-Observation Stability ===")
print(f"⟨dS_meta/dt⟩={meta_drift:.3e} | Corr_meta={corr_meta:.3f} | {cls}")
print("✅ Results saved → backend/modules/knowledge/O7_self_observation.json")