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
gamma_S = 3.0       # entropy feedback gain
gamma_kappa = 2.0   # curvature feedback gain
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

# === curvature estimator ===
def curvature(arr):
    grad = np.gradient(arr)
    grad2 = np.gradient(grad)
    with np.errstate(divide='ignore', invalid='ignore'):
        kappa = np.nanmean(np.abs(grad2) / (np.abs(grad)+1e-9))
    return float(np.nan_to_num(kappa))

# === evolution ===
def evolve_entropy_curv_locked(phi0):
    Phi = np.zeros((T, N))
    Phi[0] = phi0.copy()

    k = np.array([0.2, 0.6, 0.2])
    k /= k.sum()
    S = np.zeros(T)
    S[0] = np.log(np.sum(Phi[0]**2) + 1e-12)
    K = np.zeros(T)
    K[0] = curvature(Phi[0])

    for t in range(1, T):
        xp = np.pad(Phi[t-1], (1,1), mode="wrap")
        Phi[t] = k[0]*xp[:-2] + k[1]*xp[1:-1] + k[2]*xp[2:]

        # Compute entropy + curvature
        S[t] = np.log(np.sum(Phi[t]**2) + 1e-12)
        K[t] = curvature(Phi[t])

        dS = (S[t] - S[t-1]) / dt
        if t > 200:
            mean_dS = np.mean(np.diff(S[t-200:t]))
            mean_K = np.mean(K[t-200:t])
        else:
            mean_dS = np.mean(np.diff(S[:t])) if t > 2 else 0.0
            mean_K = np.mean(K[:t]) if t > 1 else K[0]

        # Combined feedback
        fb_entropy = -gamma_S * (dS - mean_dS)
        fb_curv = -gamma_kappa * (K[t] - mean_K)
        feedback = np.exp(fb_entropy + fb_curv)
        feedback = np.clip(feedback, 0.2, 5.0)

        noise_amp = base_noise * feedback
        Phi[t] += noise_amp * rng.normal(0, 1, N)

        # Energy renormalization
        E = np.sum(Phi[t]**2)
        if not np.isfinite(E) or E < 1e-12:
            Phi[t] = Phi[t-1].copy()
        else:
            Phi[t] *= np.sqrt(np.sum(Phi[0]**2) / E)

    return Phi, S, K

# === metrics ===
def analyze(Phi, S, K):
    mean_phi = float(np.nanmean(Phi[-200:]))
    curv = float(np.polyfit(np.log(np.arange(1, N+1)), np.log(np.abs(Phi[-1])+1e-9), 1)[0])
    entropy_rate = float(np.nanmean(np.gradient(S[-400:], dt)))
    mean_curv = float(np.mean(K[-400:]))
    return mean_phi, curv, entropy_rate, mean_curv

metrics = {"Phi_mean": [], "curv_exp": [], "entropy_rate": [], "mean_curv": []}

for name in IC_types:
    Phi, S, K = evolve_entropy_curv_locked(make_ic(name))
    m = analyze(Phi, S, K)
    for k, v in zip(metrics.keys(), m):
        metrics[k].append(v)

# === collapse measure ===
def rms_dev(a):
    a = np.array(a)
    if np.any(~np.isfinite(a)): return np.nan
    return float(np.sqrt(np.nanmean((a - np.nanmean(a))**2)))

collapse = {k: rms_dev(metrics[k]) for k in metrics.keys()}

if all(np.isfinite(list(collapse.values()))) and all(v < 0.05 for v in collapse.values()):
    verdict = "✅ Geometry invariant"
elif all(np.isfinite(list(collapse.values()))) and all(v < 0.1 for v in collapse.values()):
    verdict = "⚠️ Marginal geometry lock"
else:
    verdict = "❌ IC-dependent geometry"

# === plot ===
fig, ax = plt.subplots(figsize=(8,5))
for i, name in enumerate(IC_types):
    ax.scatter(metrics["Phi_mean"][i], metrics["curv_exp"][i], s=120, label=name)
ax.set_xlabel("⟨Φ⟩ / normalized")
ax.set_ylabel("Curvature exponent")
ax.set_title("E6d — Curvature-Adaptive Entropy Lock")
ax.legend(); ax.grid(True)
plt.tight_layout()
plt.savefig("PAEV_E6d_CurvatureAdaptiveUniversality.png", dpi=160)

# === save ===
out = {
    "IC_types": IC_types,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "params": {"N": N, "T": T, "dt": dt, "base_noise": base_noise,
               "gamma_S": gamma_S, "gamma_kappa": gamma_kappa},
    "metrics": metrics,
    "collapse_dev": collapse,
    "classification": verdict,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = "backend/modules/knowledge/E6d_curvature_adaptive_universality.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E6d — Curvature-Adaptive Entropy Lock ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved → {save_path}")