import numpy as np, json, time, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

# --- constants loader ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameters ---
GRID_SCALES = [
    {"N": 256, "dt": 0.01},
    {"N": 512, "dt": 0.005},
    {"N": 1024, "dt": 0.0025},
]
noise_amp = 0.03
seed0 = int(time.time())

metrics = {"E_mean": [], "Phi_std": [], "TH": []}

# --- runs ---
for i, cfg in enumerate(GRID_SCALES):
    np.random.seed(seed0)
    N, dt = cfg["N"], cfg["dt"]
    t = np.arange(0, 1000, dt)
    phi0 = np.random.uniform(0, 2*np.pi)
    noise = np.random.normal(0, noise_amp, len(t))

    # synthetic field evolution
    Phi = np.cos(0.01 * t + phi0) + 0.002 * np.cumsum(noise)
    E = 0.5 * (ħ * Phi**2 + G * np.gradient(Phi)**2)

    # stability time
    lock_index = np.where(np.abs(np.gradient(Phi)) < 1e-3)[0]
    TH = t[lock_index[0]] if len(lock_index) > 0 else np.nan

    metrics["E_mean"].append(np.nanmean(E))
    metrics["Phi_std"].append(np.nanstd(Phi))
    metrics["TH"].append(TH)

# --- analysis ---
def cv(arr): 
    arr = np.array(arr)
    return np.nanstd(arr) / np.nanmean(np.abs(arr))

CVs = {k: float(cv(v)) for k, v in metrics.items()}

classification = (
    "✅ Stable law" if all(v < 0.05 for v in CVs.values())
    else "⚠️ Marginal universality" if any(v < 0.1 for v in CVs.values())
    else "❌ Numerical instability"
)

# --- visualization ---
plt.figure(figsize=(9,5))
x = [cfg["N"] for cfg in GRID_SCALES]
plt.plot(x, metrics["E_mean"], "o-", label="⟨E⟩")
plt.plot(x, metrics["Phi_std"], "s--", label="σ(Φ)")
plt.plot(x, metrics["TH"], "d-.", label="T_H")
plt.xlabel("Grid size N")
plt.ylabel("Metric value")
plt.title("E2 — Discretization Invariance Test")
plt.legend(); plt.grid(True); plt.tight_layout()
plt.savefig("PAEV_E2_Discretization.png", dpi=160)

# --- save ---
out = {
    "grid_scales": GRID_SCALES,
    "noise_amp": noise_amp,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "metrics": metrics,
    "CVs": CVs,
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = Path("backend/modules/knowledge/E2_discretization.json")
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

# --- log ---
print("=== E2 — Discretization Universality ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved → {save_path}")