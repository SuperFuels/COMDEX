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
learning_rate = 0.05
feedback_gain = 0.18
meta_gain = 0.12
recursive_gain = 0.08
noise_scale = 0.007

# --- initial states ---
S_system = [0.72]
S_observer = [0.70]
S_pred = [0.68]
S_meta = [0.66]

# --- evolution loop ---
for t in range(1, n_steps):
    noise = np.random.normal(0, noise_scale)

    # meta-layer predicts its own predictive state (self-reflection)
    dS_meta = recursive_gain * (S_pred[-1] - S_meta[-1]) + 0.5 * noise

    # prediction layer forecasts observer state and adjusts using meta correction
    dS_pred = feedback_gain * (S_observer[-1] - S_pred[-1]) + meta_gain * (S_meta[-1] - S_pred[-1]) + noise

    # observer responds to both system and prediction
    dS_obs = learning_rate * (S_system[-1] - S_observer[-1]) + feedback_gain * (S_pred[-1] - S_observer[-1])

    # system drift (weakly coupled external environment)
    dS_sys = -0.0002 * (S_system[-1] - 0.71) + np.random.normal(0, noise_scale / 2)

    # update states
    S_system.append(S_system[-1] + dS_sys)
    S_observer.append(S_observer[-1] + dS_obs)
    S_pred.append(S_pred[-1] + dS_pred)
    S_meta.append(S_meta[-1] + dS_meta)

# --- convert to arrays ---
S_system = np.array(S_system)
S_observer = np.array(S_observer)
S_pred = np.array(S_pred)
S_meta = np.array(S_meta)

# --- metrics ---
meta_drift = np.mean(np.gradient(S_meta))
corr_meta = np.corrcoef(S_meta, S_pred)[0, 1]
meta_coherence = np.std(S_meta - S_pred)

# classification logic
if abs(meta_drift) < 1e-4 and corr_meta > 0.9 and meta_coherence < 0.02:
    cls = "✅ Self-coherent awareness"
elif abs(meta_drift) < 5e-4 and corr_meta > 0.7:
    cls = "⚠️ Marginal recursion"
else:
    cls = "❌ Divergent feedback loop"

# --- plotting ---
os.makedirs("backend/modules/knowledge", exist_ok=True)

plt.figure(figsize=(9, 5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_pred, label="S_pred (forecast)")
plt.plot(S_meta, label="S_meta (self-reflective)")
plt.title("P2 — Recursive Awareness Coupling")
plt.xlabel("time step")
plt.ylabel("Entropy")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P2_RecursiveAwareness.png", dpi=120)

# --- summary data ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "learning_rate": learning_rate,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "recursive_gain": recursive_gain,
    "noise_scale": noise_scale,
    "meta_drift": float(meta_drift),
    "corr_meta": float(corr_meta),
    "meta_coherence": float(meta_coherence),
    "classification": cls,
    "files": {"plot": "PAEV_P2_RecursiveAwareness.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/P2_recursive_awareness.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== P2 — Recursive Awareness Coupling ===")
print(f"⟨dS_meta/dt⟩={meta_drift:.3e} | Corr_meta={corr_meta:.3f} | Coherence={meta_coherence:.3f} | {cls}")
print("✅ Results saved → backend/modules/knowledge/P2_recursive_awareness.json")