import numpy as np, json
from pathlib import Path
from datetime import datetime, timezone
import matplotlib.pyplot as plt

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameters ---
N = 512
T = 2500
dt = 0.01
base_noise = 0.008
rng = np.random.default_rng(1234)

IC_types = ["hot_shell", "cold_spike", "multi_blob"]

x = np.linspace(-1, 1, N)

# --- initial conditions ---
def hot_shell():
    return np.exp(-((x)**2)/0.05)

def cold_spike():
    phi = np.zeros_like(x)
    phi[N//2] = 1.0
    return phi

def multi_blob():
    centers = [-0.4, 0.0, 0.4]
    return sum(np.exp(-((x-c)**2)/0.01) for c in centers)

ic_funcs = [hot_shell, cold_spike, multi_blob]

# --- diffusion evolution with energy renormalization ---
def evolve_field(phi0):
    Phi = np.zeros((T, N))
    Phi[0] = phi0.copy()
    k = np.array([0.2, 0.6, 0.2])
    k /= k.sum()

    for t in range(1, T):
        xp = np.pad(Phi[t-1], (1,1), mode="wrap")
        Phi[t] = k[0]*xp[:-2] + k[1]*xp[1:-1] + k[2]*xp[2:]
        noise_amp = base_noise * (1 + 0.1*np.sin(0.002*t))
        Phi[t] += noise_amp * rng.normal(0, 1, N)
        # renormalize total energy
        Phi[t] *= np.sqrt(np.sum(Phi[0]**2) / np.sum(Phi[t]**2))
    return Phi

# --- compute metrics ---
def analyze(Phi):
    mean_phi = np.mean(Phi[-200:])
    curv = np.polyfit(np.log(np.arange(1, N+1)), np.log(np.abs(Phi[-1])+1e-9), 1)[0]
    S = np.log(np.sum(Phi**2, axis=1) + 1e-12)
    entropy_rate = np.mean(np.diff(S))
    return mean_phi, curv, entropy_rate

metrics = {"Phi_mean": [], "curv_exp": [], "entropy_rate": []}

for f in ic_funcs:
    Phi = evolve_field(f())
    m = analyze(Phi)
    for key, val in zip(metrics.keys(), m):
        metrics[key].append(val)

# --- G10b renormalization (variance normalization) ---
for k in metrics.keys():
    arr = np.array(metrics[k])
    arr = (arr - np.mean(arr)) / (np.std(arr) + 1e-12)
    metrics[k] = list(arr / np.nanmean(np.abs(arr)))

def rms_dev(a): return float(np.sqrt(np.nanmean((np.array(a) - 1)**2)))
collapse = {k: rms_dev(metrics[k]) for k in metrics.keys()}

# --- classification ---
verdict = (
    "✅ Universal scaling"
    if all(v < 0.05 for v in collapse.values())
    else "⚠️ Marginal universality"
    if all(v < 0.1 for v in collapse.values())
    else "❌ IC-dependent dynamics"
)

# --- visualization ---
fig, ax = plt.subplots(figsize=(8,5))
for i, label in enumerate(IC_types):
    ax.scatter(metrics["Phi_mean"][i], metrics["curv_exp"][i], s=90, label=label)
ax.set_xlabel("⟨Φ⟩ / G10b norm")
ax.set_ylabel("Curvature exponent / norm")
ax.set_title("E6b - Cross-IC Universality (Stabilized)")
ax.legend(); ax.grid(True)
plt.tight_layout()
plt.savefig("PAEV_E6b_ICUniversality.png", dpi=160)

# --- save results ---
out = {
    "IC_types": IC_types,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "noise_amp": base_noise,
    "metrics": metrics,
    "collapse_dev": collapse,
    "classification": verdict,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = "backend/modules/knowledge/E6b_initial_condition_universal.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E6b - Cross-Initial-Condition Universality (Stabilized) ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved -> {save_path}")