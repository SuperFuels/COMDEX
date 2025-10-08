import numpy as np, json, time, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

# --- constants loader ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameters ---
N_ENSEMBLE = 64
noise_amp = 0.05
seed0 = int(time.time())
metrics = {"Phi_mean": [], "TH": [], "tP": []}

# --- ensemble runs ---
for i in range(N_ENSEMBLE):
    np.random.seed(seed0 + i)
    phi0 = np.random.uniform(0, 2*np.pi)
    t = np.linspace(0, 1000, 10000)
    noise = np.random.normal(0, noise_amp, len(t))
    Phi = np.cos(0.01*t + phi0) + 0.001*np.cumsum(noise)

    lock_index = np.where(np.abs(np.gradient(Phi)) < 1e-3)[0]
    TH = t[lock_index[0]] if len(lock_index) > 0 else np.nan
    tP = 2*np.pi / 0.01

    metrics["Phi_mean"].append(np.mean(Phi))
    metrics["TH"].append(TH)
    metrics["tP"].append(tP)

# --- analysis ---
def cv(arr): 
    arr = np.array(arr)
    return np.nanstd(arr) / np.nanmean(np.abs(arr))

CVs = {k: float(cv(v)) for k, v in metrics.items()}

classification = (
    "✅ Stable law" if all(v < 0.05 for v in CVs.values())
    else "⚠️ Marginal reproducibility" if any(v < 0.1 for v in CVs.values())
    else "❌ Chaotic dispersion"
)

# --- save results ---
out = {
    "N_ensemble": N_ENSEMBLE,
    "noise_amp": noise_amp,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "CVs": CVs,
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = Path("backend/modules/knowledge/E1_ensemble_repro.json")
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

# --- visualization ---
plt.hist(metrics["Phi_mean"], bins=20)
plt.title("E1 — Ensemble Φ Mean Distribution")
plt.xlabel("⟨Φ⟩"); plt.ylabel("count")
plt.grid(True); plt.tight_layout()
plt.savefig("PAEV_E1_EnsemblePhiHist.png", dpi=160)

# --- log ---
print("=== E1 — Ensemble Reproducibility ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved → {save_path}")