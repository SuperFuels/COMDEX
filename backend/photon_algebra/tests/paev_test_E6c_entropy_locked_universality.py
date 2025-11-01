import numpy as np, json
from pathlib import Path
from datetime import datetime, timezone
import matplotlib.pyplot as plt
from backend.photon_algebra.utils.load_constants import load_constants

# === constants ===
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# === parameters ===
N = 512
T = 3000
dt = 0.01
base_noise = 0.008
feedback_gamma = 3.0
rng = np.random.default_rng(2025)

IC_types = ["hot_shell", "cold_spike", "multi_blob"]
x = np.linspace(-1, 1, N)

# === initial conditions ===
def make_ic(name):
    if name == "hot_shell":
        return np.exp(-((x)**2)/0.05)
    elif name == "cold_spike":
        phi = np.zeros_like(x)
        phi[N//2] = 1.0
        return phi
    elif name == "multi_blob":
        centers = [-0.4, 0.0, 0.4]
        return sum(np.exp(-((x-c)**2)/0.01) for c in centers)
    else:
        raise ValueError(name)

# === evolution ===
def evolve_entropy_locked(phi0):
    Phi = np.zeros((T, N))
    Phi[0] = phi0.copy()

    k = np.array([0.2, 0.6, 0.2])
    k /= k.sum()
    S = np.zeros(T)
    S[0] = np.log(np.sum(Phi[0]**2) + 1e-12)

    for t in range(1, T):
        xp = np.pad(Phi[t-1], (1,1), mode="wrap")
        Phi[t] = k[0]*xp[:-2] + k[1]*xp[1:-1] + k[2]*xp[2:]

        # Entropy calculation
        S[t] = np.log(np.sum(Phi[t]**2) + 1e-12)
        dS = (S[t] - S[t-1]) / dt

        # Smooth entropy derivative average (avoid empty slice)
        if t > 200:
            mean_Sdot = np.mean(np.diff(S[t-200:t]))
        else:
            mean_Sdot = np.mean(np.diff(S[:t])) if t > 2 else 0.0

        # Feedback-controlled noise (clipped for stability)
        feedback = np.exp(-feedback_gamma * (dS - mean_Sdot))
        feedback = np.clip(feedback, 0.2, 5.0)
        noise_amp = base_noise * feedback

        Phi[t] += noise_amp * rng.normal(0, 1, N)

        # Energy renormalization (with safeguard)
        E = np.sum(Phi[t]**2)
        if not np.isfinite(E) or E < 1e-12:
            Phi[t] = Phi[t-1].copy()
        else:
            Phi[t] *= np.sqrt(np.sum(Phi[0]**2) / E)

    return Phi, S

# === metrics ===
def analyze(Phi, S):
    mean_phi = float(np.nanmean(Phi[-200:]))
    curv = float(np.polyfit(np.log(np.arange(1, N+1)), np.log(np.abs(Phi[-1])+1e-9), 1)[0])
    entropy_rate = float(np.nanmean(np.gradient(S[-400:], dt)))
    return mean_phi, curv, entropy_rate

metrics = {"Phi_mean": [], "curv_exp": [], "entropy_rate": []}

for name in IC_types:
    Phi, S = evolve_entropy_locked(make_ic(name))
    m = analyze(Phi, S)
    for k, v in zip(metrics.keys(), m):
        metrics[k].append(v)

# === collapse diagnostics ===
def rms_dev(a):
    a = np.array(a)
    if np.any(~np.isfinite(a)):
        return np.nan
    return float(np.sqrt(np.nanmean((a - np.nanmean(a))**2)))

collapse = {k: rms_dev(metrics[k]) for k in metrics.keys()}

if all(np.isfinite(list(collapse.values()))) and all(v < 0.05 for v in collapse.values()):
    verdict = "✅ Entropy-locked universality"
elif all(np.isfinite(list(collapse.values()))) and all(v < 0.1 for v in collapse.values()):
    verdict = "⚠️ Marginal entropy-locking"
else:
    verdict = "❌ IC-dependent (feedback insufficient)"

# === plot ===
fig, ax = plt.subplots(figsize=(8,5))
for i, name in enumerate(IC_types):
    ax.scatter(metrics["Phi_mean"][i], metrics["curv_exp"][i], s=120, label=name)
ax.set_xlabel("⟨Φ⟩ / normalized")
ax.set_ylabel("Curvature exponent")
ax.set_title("E6c - Entropy-Locked Cross-IC Universality (Stabilized)")
ax.legend(); ax.grid(True)
plt.tight_layout()
plt.savefig("PAEV_E6c_EntropyLockedUniversality.png", dpi=160)

# === save results ===
out = {
    "IC_types": IC_types,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "params": {"N": N, "T": T, "dt": dt, "base_noise": base_noise, "feedback_gamma": feedback_gamma},
    "metrics": metrics,
    "collapse_dev": collapse,
    "classification": verdict,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = "backend/modules/knowledge/E6c_entropy_locked_universality.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E6c - Entropy-Locked Universality (Stabilized) ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved -> {save_path}")