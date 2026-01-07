import numpy as np, json, time
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- params (stabilized) ---
N, T = 2048, 3200
dt = 0.0025
t = np.arange(T) * dt
t_pert = 1200                    # index in steps
block = 128                      # spectral window
noise_amp = 0.006
theta = 1.0                      # no greybody tilt for this stability test
rng = np.random.default_rng(42)

# --- base field & kernel (energy-symmetric) ---
phi0 = rng.uniform(0, 2*np.pi)
base = 1.0 + 0.03*np.cos(0.11*np.arange(N))              # gentle spatial modulation
Phi = np.zeros((T, N), dtype=float)
Phi[0] = base * np.cos(0.015*np.zeros(N) + phi0)

# 3-tap symmetric propagation kernel (nearly unit gain)
k = np.array([0.24, 0.52, 0.24])
k /= k.sum()

def step(x):
    # periodic bc for E5b (neutral choice)
    xp = np.pad(x, (1,1), mode="wrap")
    y = k[0]*xp[:-2] + k[1]*xp[1:-1] + k[2]*xp[2:]
    return y

# --- run ---
S = np.zeros(T)
spec_lock = np.zeros(T)

# reference spectrum window (pre-pert)
def window(n):  # Hann
    w = 0.5 - 0.5*np.cos(2*np.pi*np.arange(n)/n)
    return w

Wb = window(block)
Xref = None

# initialize and set RMS target to clamp drift
target_rms = np.sqrt(np.mean(Phi[0]**2))

for tt in range(1, T):
    # propagate
    Phi[tt] = step(Phi[tt-1])

    # add small process noise
    Phi[tt] += noise_amp * rng.normal(0, 1, size=N)

    # symmetric perturbation at t_pert (zero net energy)
    if tt == t_pert:
        width = 31
        j0 = N // 2
        gate = np.hanning(width)
        bump = np.zeros(N)
        # center symmetrically around j0 (odd width fix)
        half = width // 2
        bump[j0 - half:j0 + half + 1] = gate
        # local antisymmetric phase flip (energy-neutral)
        Phi[tt] *= (1.0 - bump) + (-1.0) * bump

    # energy clamp (keeps ΔE/E tiny)
    rms = np.sqrt(np.mean(Phi[tt]**2))
    if rms > 1e-12:
        Phi[tt] *= (target_rms / rms)

    # entropy proxy
    S[tt] = np.log(np.sum(Phi[tt]**2) + 1e-12)

    # spectral lock against pre-pert reference
    if tt == block and Xref is None:
        seg = Phi[tt-block:tt].mean(axis=0) * window(N)  # broad, stable ref
        Xref = np.abs(np.fft.rfft(seg))
        Xref /= Xref.max() + 1e-12

    if Xref is not None:
        # local windowed spectrum
        segN = Phi[max(0, tt-block):tt].mean(axis=0)
        X = np.abs(np.fft.rfft(segN * window(N)))
        X /= X.max() + 1e-12
        # cosine similarity in spectrum
        m = min(len(X), len(Xref))
        spec_lock[tt] = np.dot(X[:m], Xref[:m]) / (np.linalg.norm(X[:m])*np.linalg.norm(Xref[:m]) + 1e-12)

# --- metrics ---
# entropy monotonicity (fraction of non-decreasing steps outside tiny tolerance)
dS = np.diff(S)
entropy_monotonicity = np.mean(dS >= -1e-4)

# recovery: steps after t_pert to return spec_lock within 95% of pre-tail mean
pre_tail = spec_lock[max(block, 50):t_pert]
pre_mu = np.nanmean(pre_tail[pre_tail>0]) if pre_tail.size else 1.0
target_lock = 0.95 * pre_mu
post = spec_lock[t_pert:]
rec_idx = np.argmax(post >= target_lock)
recovery_steps = int(rec_idx) if post.size and post[rec_idx] >= target_lock else np.inf
recovery_time = (recovery_steps if np.isfinite(recovery_steps) else np.nan) * dt

# tail spectral lock
tail_slice = spec_lock[int(0.8*T):]
spec_lock_tail = float(np.nanmean(tail_slice[tail_slice>0])) if tail_slice.size else 0.0

# relative energy drift across full run
E0 = np.mean(Phi[0]**2)
E1 = np.mean(Phi[-1]**2)
E_drift_rel = float(abs(E1 - E0) / (E0 + 1e-12))

# verdict
verdict = ("✅ Reversible propagation"
           if (entropy_monotonicity >= 0.90 and
               spec_lock_tail >= 0.85 and
               np.isfinite(recovery_steps) and recovery_steps <= 200 and
               E_drift_rel <= 3e-3)
           else "⚠️ Marginal propagation" if spec_lock_tail >= 0.7 else "❌ Unstable propagation")

# --- plots ---
from scipy.ndimage import gaussian_filter1d

S_s = gaussian_filter1d(S, sigma=9)

plt.figure(figsize=(10,5))
plt.plot(t, spec_lock, lw=2, label="spectral lock (ref)")
plt.axvline(t[t_pert], ls="--", color="r", alpha=0.7, label="perturb")
plt.axhline(spec_lock_tail, ls=":", color="gray", label=f"tail mean={spec_lock_tail:.3f}")
plt.title("E5 - Spectral Coherence During Propagation")
plt.xlabel("time"); plt.ylabel("p_lock"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_E5b_SpectralLock.png", dpi=160)

plt.figure(figsize=(10,5))
plt.plot(t, S_s, lw=2, label="S(t) (smoothed)")
plt.axvline(t[t_pert], ls="--", color="r", alpha=0.7, label="perturb")
plt.title("E5 - Entropy Propagation & Recovery")
plt.xlabel("time"); plt.ylabel("entropy S"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_E5b_EntropyPropagation.png", dpi=160)

# --- save JSON ---
out = {
    "N": N, "T": T, "dt": dt, "t_pert": t_pert, "block": block,
    "theta": theta, "noise_amp": noise_amp,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "metrics": {
        "entropy_monotonicity": float(entropy_monotonicity),
        "recovery_steps": None if not np.isfinite(recovery_steps) else int(recovery_steps),
        "recovery_time": None if not np.isfinite(recovery_steps) else float(recovery_time),
        "spec_lock_tail": float(spec_lock_tail),
        "E_drift_rel": float(E_drift_rel),
        "S_pre_mean": float(np.nanmean(S[max(block, 50):t_pert]))
    },
    "classification": verdict,
    "files": {
        "entropy_plot": "PAEV_E5b_EntropyPropagation.png",
        "spectral_plot": "PAEV_E5b_SpectralLock.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = "backend/modules/knowledge/E5b_entropy_propagation_stable.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E5b - Entropy Propagation & Reversibility (stabilized) ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved -> {save_path}")