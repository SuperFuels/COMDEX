import numpy as np, json, time, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
from scipy.ndimage import gaussian_filter1d
from backend.photon_algebra.utils.load_constants import load_constants

# --- Load unified constants ---
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameters ---
N = 512
T = 2000
noise_levels = [0.005, 0.01, 0.02, 0.03]
greybody_temp = [0.8, 1.0, 1.2]  # relative spectral skew
seed0 = int(time.time())

metrics = {"E_drift": [], "curv_std": [], "spectral_lock": []}

x = np.linspace(-25, 25, N)
t = np.linspace(0, 500, T)
base = np.exp(-x**2 / 200)

def greybody_spectrum(x, temp):
    # Planck-like spectral profile (simplified)
    return 1 / (np.exp(np.abs(x)/temp) - 1 + 1e-6)

for nl in noise_levels:
    for temp in greybody_temp:
        np.random.seed(seed0)
        phi0 = np.random.uniform(0, 2*np.pi)
        Phi = base[:, None] * np.cos(0.02 * t[None, :] + phi0)
        Phi += 0.001*np.cumsum(np.random.normal(0, nl, (N,T)), axis=1)

        # apply greybody weighting along spatial axis
        gb = greybody_spectrum(x, temp)
        Phi *= gb[:,None]

        # curvature energy proxy
        grad = np.gradient(Phi, axis=0)
        curv = np.gradient(grad, axis=0)
        curv_s = gaussian_filter1d(curv.mean(axis=1), sigma=2)

        E = np.sum(Phi**2, axis=0)
        E_drift = (E[-1] - E[0]) / (np.mean(E) + 1e-9)
        curv_std = np.std(curv_s)

        # spectral lock: correlation of greybody weighting with curvature
        corr = np.corrcoef(gb, np.abs(curv_s))[0,1]

        metrics["E_drift"].append(E_drift)
        metrics["curv_std"].append(curv_std)
        metrics["spectral_lock"].append(corr)

def cv(arr): 
    arr = np.array(arr)
    return np.nanstd(arr)/np.nanmean(np.abs(arr))

CVs = {k: float(cv(v)) for k,v in metrics.items()}
classification = (
    "✅ Stable under noise + greybody perturbations"
    if (max(np.abs(metrics["E_drift"])) < 0.05 and 
        np.nanmean(metrics["curv_std"]) < 0.2 and 
        np.nanmean(metrics["spectral_lock"]) > 0.6)
    else "⚠️ Marginal stability" if np.nanmean(metrics["spectral_lock"]) > 0.4
    else "❌ Unstable response"
)

# --- Plot summary ---
plt.figure(figsize=(8,5))
plt.scatter(metrics["E_drift"], metrics["curv_std"], c=metrics["spectral_lock"], cmap="plasma", s=80)
plt.colorbar(label="Spectral lock")
plt.title("E4 — Noise & Greybody Perturbation Stability")
plt.xlabel("Energy drift ΔE/⟨E⟩")
plt.ylabel("Curvature std")
plt.grid(True); plt.tight_layout()
plt.savefig("PAEV_E4_NoiseGreybody.png", dpi=160)

# --- Save JSON ---
out = {
    "N": N, "T": T,
    "noise_levels": noise_levels,
    "greybody_temp": greybody_temp,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "metrics": metrics,
    "CVs": CVs,
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = Path("backend/modules/knowledge/E4_noise_greybody.json")
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E4 — Noise & Greybody Perturbation Stability ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved → {save_path}")