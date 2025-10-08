import numpy as np, json, time
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameters ---
N = 512
T = 2000
dt = 0.01
noise_amp = 0.01
rng = np.random.default_rng(42)

IC_types = ["hot_shell", "cold_spike", "multi_blob"]

def evolve_field(phi0, label):
    """Simple diffusion-curvature propagation."""
    Phi = np.zeros((T, N))
    Phi[0] = phi0.copy()
    k = np.array([0.24, 0.52, 0.24])
    k /= k.sum()

    for t in range(1, T):
        xp = np.pad(Phi[t-1], (1,1), mode="wrap")
        Phi[t] = k[0]*xp[:-2] + k[1]*xp[1:-1] + k[2]*xp[2:]
        Phi[t] += noise_amp * rng.normal(0, 1, N)
    return Phi

# --- initial conditions ---
x = np.linspace(-1, 1, N)

def hot_shell():
    return np.exp(-((x)**2)/0.05)

def cold_spike():
    phi = np.zeros_like(x)
    phi[N//2] = 1.0
    return phi

def multi_blob():
    centers = [-0.4, 0.0, 0.4]
    phi = sum(np.exp(-((x-c)**2)/0.01) for c in centers)
    return phi

ic_funcs = [hot_shell, cold_spike, multi_blob]

# --- run ensemble ---
metrics = {"Phi_mean": [], "curv_exp": [], "entropy_rate": []}

for f, label in zip(ic_funcs, IC_types):
    Phi = evolve_field(f(), label)
    mean_phi = np.mean(Phi[-200:])
    curv = np.polyfit(np.log(np.arange(1, N+1)), np.log(np.abs(Phi[-1])+1e-9), 1)[0]
    S = np.log(np.sum(Phi**2, axis=1) + 1e-12)
    entropy_rate = np.mean(np.diff(S))
    metrics["Phi_mean"].append(mean_phi)
    metrics["curv_exp"].append(curv)
    metrics["entropy_rate"].append(entropy_rate)

# --- G10b scaling (normalize for comparison) ---
for k in metrics.keys():
    arr = np.array(metrics[k])
    metrics[k] = list(arr / np.nanmean(arr))

# --- collapse deviation ---
def rms_dev(a):
    return float(np.sqrt(np.nanmean((a - 1)**2)))

collapse = {k: rms_dev(np.array(metrics[k])) for k in metrics.keys()}

# --- classification ---
verdict = (
    "✅ Universal scaling"
    if all(v < 0.05 for v in collapse.values())
    else "⚠️ Marginal universality"
    if any(v < 0.1 for v in collapse.values())
    else "❌ IC-dependent dynamics"
)

# --- visualization ---
fig, ax = plt.subplots(figsize=(8,5))
for i, label in enumerate(IC_types):
    ax.scatter(metrics["Phi_mean"][i], metrics["curv_exp"][i], s=80, label=label)
ax.set_xlabel("⟨Φ⟩ / G10b norm")
ax.set_ylabel("Curvature exponent / norm")
ax.set_title("E6 — Cross-IC Universality Test")
ax.legend(); ax.grid(True)
plt.tight_layout()
plt.savefig("PAEV_E6_ICUniversality.png", dpi=160)

# --- save JSON ---
out = {
    "IC_types": IC_types,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "noise_amp": noise_amp,
    "metrics": metrics,
    "collapse_dev": collapse,
    "classification": verdict,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = "backend/modules/knowledge/E6_initial_condition_sweep.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E6 — Cross-Initial-Condition Universality ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved → {save_path}")