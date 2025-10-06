import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- setup ---
np.random.seed(42)
x = np.linspace(-5, 5, 800)
dx = x[1] - x[0]
t_steps = 600

# base wavefunctions
psi_sys = np.exp(-x**2) * np.exp(1j * 0.4 * x)
psi_obs = np.exp(-1.2*x**2) * np.exp(1j * 0.3 * x)
psi_sys /= np.sqrt(np.trapezoid(np.abs(psi_sys)**2, x))
psi_obs /= np.sqrt(np.trapezoid(np.abs(psi_obs)**2, x))

# coupling parameters
coupling = 0.22
noise_scale = 0.012
decay_rate = 0.001

# --- simulation ---
F, S, P_pred = [], [], []
collapse_threshold = 0.8
collapse_time = None

def fidelity(a, b):
    na = np.sqrt(np.trapezoid(np.abs(a)**2, x))
    nb = np.sqrt(np.trapezoid(np.abs(b)**2, x))
    return np.abs(np.trapezoid(np.conj(a)*b, x) / (na * nb))

for t in range(t_steps):
    # noise + decoherence
    psi_sys *= np.exp(-decay_rate*t) * np.exp(1j * np.random.normal(0, noise_scale, len(x)))
    psi_obs *= np.exp(-decay_rate*t) * np.exp(-1j * np.random.normal(0, noise_scale, len(x)))
    
    psi_sys /= np.sqrt(np.trapezoid(np.abs(psi_sys)**2, x))
    psi_obs /= np.sqrt(np.trapezoid(np.abs(psi_obs)**2, x))
    
    # entropy proxy
    p_sys = np.abs(psi_sys)**2
    S.append(-np.trapezoid(p_sys * np.log(p_sys + 1e-12), x))
    
    # fidelity (entanglement coherence proxy)
    F.append(fidelity(psi_sys, psi_obs))
    
    # simple predictive model: entropy drift anticipates fidelity fall
    if t > 2:
        drift = S[-1] - S[-3]
        pred = max(0.0, min(1.0, 1 - abs(drift)*50))
        P_pred.append(pred)
    else:
        P_pred.append(1.0)
    
    # check collapse
    if F[-1] < collapse_threshold and collapse_time is None:
        collapse_time = t

# --- metrics ---
mean_S_drift = np.mean(np.diff(S)[-50:])
mean_P_pred = np.mean(P_pred)
final_F = F[-1]
collapse_time = collapse_time if collapse_time is not None else t_steps

# --- classification ---
if final_F > 0.9 and mean_P_pred > 0.8:
    cls = "✅ Predictive stable coupling"
elif final_F > 0.8:
    cls = "⚠️ Late collapse prediction"
elif mean_P_pred < 0.5:
    cls = "❌ Chaotic / Unpredictable"
else:
    cls = "🌀 Transitional collapse regime"

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9,5))
plt.plot(F, label="Fidelity (Entanglement)")
plt.plot(P_pred, label="Prediction Confidence", linestyle="--")
plt.axhline(y=collapse_threshold, color="r", linestyle=":", label="Collapse threshold")
plt.title("O5 — Observer-State Collapse Prediction")
plt.xlabel("time step")
plt.ylabel("Fidelity / Confidence")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_O5_CollapsePrediction.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "coupling": coupling,
    "noise_scale": noise_scale,
    "decay_rate": decay_rate,
    "final_fidelity": float(final_F),
    "mean_S_drift": float(mean_S_drift),
    "mean_P_pred": float(mean_P_pred),
    "collapse_time": int(collapse_time),
    "classification": cls,
    "files": {
        "plot": "PAEV_O5_CollapsePrediction.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/O5_collapse_prediction.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== O5 — Observer-State Collapse Prediction ===")
print(f"Final Fidelity={final_F:.3f} | ⟨S_drift⟩={mean_S_drift:.3e} | ⟨P_pred⟩={mean_P_pred:.3f}")
print(f"Classification: {cls}")
print("✅ Results saved → backend/modules/knowledge/O5_collapse_prediction.json")