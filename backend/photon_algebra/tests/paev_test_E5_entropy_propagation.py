import numpy as np, json, time, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

# --- load constants (registry-coherent) ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --------------------
# E5 — Entropy Propagation & Reversibility
# --------------------

# --- parameters ---
N = 1024                 # spatial grid
T = 2200                 # time steps
dt = 0.005
x = np.linspace(0, 2*np.pi, N, endpoint=False)
t = np.arange(T) * dt

noise_amp = 0.015
seed = int(time.time())
rng = np.random.default_rng(seed)

# perturbation ("information shuffle") — blockwise permutation at t_pert
t_pert = 800
block = 64                          # must divide N
assert N % block == 0
blocks = N // block

# small greybody-like spectral skew applied throughout (matches E4 style)
theta = 1.05                         # 1.0 = blackbody-like, >1 adds warm skew

# --- helpers ---
def laplacian_1d(phi):
    return np.roll(phi, -1) - 2*phi + np.roll(phi, 1)

def moving_avg(y, w=21):
    # symmetric moving average for smoothing (odd window)
    if w <= 1: return y.copy()
    w = int(w) + (1 - int(w) % 2)
    k = np.ones(w) / w
    return np.convolve(y, k, mode="same")

def entropy_from_phi(phi):
    # probability from intensity with small floor to avoid log(0)
    p = np.abs(phi)**2
    p /= p.sum() + 1e-16
    p = np.clip(p, 1e-16, 1.0)
    return -(p * np.log(p)).sum()

def spectrum(phi):
    F = np.fft.rfft(phi)
    mag = np.abs(F)
    mag /= (mag.sum() + 1e-16)
    return mag

def spectral_lock(mag_a, mag_b):
    a = (mag_a - mag_a.mean())
    b = (mag_b - mag_b.mean())
    denom = (np.sqrt((a*a).sum()) * np.sqrt((b*b).sum()) + 1e-16)
    return float((a*b).sum() / denom)

# --- initialize field ---
# quasi-ordered base with two modes + phase noise
phi = 0.8*np.cos(3*x) + 0.5*np.cos(7*x + 0.3) + 0.1*np.cos(11*x + 1.1)
phi += 0.03 * rng.standard_normal(N)

# precompute a smooth spectral envelope (greybody-like)
k = np.fft.rfftfreq(N, d=(x[1]-x[0]))
grey = (k + 1.0) ** (-theta)   # gentle 1/f^theta tilt

# storage
S = np.zeros(T)
E = np.zeros(T)
R_spec = np.zeros(T)   # spectral lock vs initial
curv_std = np.zeros(T)

# initial references
spec_ref = spectrum(phi)

# --- dynamics ---
# Simple damped wave / diffusion hybrid that respects α, β scales:
#   φ̇ = α * Lap(φ) - β * φ + η(t)  (with weak nonlinearity via tanh)
# Add spectral shaping of noise in Fourier space (greybody-ish)
for ti in range(T):
    # record metrics
    S[ti] = entropy_from_phi(phi)
    dphi_dx = (np.roll(phi, -1) - np.roll(phi, 1)) / (2*(x[1]-x[0]))
    curv_std[ti] = float(np.std(dphi_dx))
    E[ti] = 0.5 * (phi@phi)/N + 0.5 * (dphi_dx@dphi_dx)/N
    R_spec[ti] = spectral_lock(spec_ref, spectrum(phi))

    # build noise in Fourier domain with greybody tilt
    nF = np.fft.rfft(rng.standard_normal(N))
    nF = nF * grey
    noise = np.fft.irfft(nF, n=N)
    noise *= noise_amp

    # base update
    phi_dot = α * laplacian_1d(phi) - β * phi + 0.15*np.tanh(phi)
    phi = phi + dt * phi_dot + np.sqrt(dt) * noise

    # information shuffle at t_pert (in-place, once)
    if ti == t_pert:
        # blockwise permutation (scramble phase-space locality)
        perm = rng.permutation(blocks)
        phi = np.concatenate([phi[j*block:(j+1)*block] for j in perm])

# --- metrics ---
# entropy monotonicity after perturbation: fraction of non-decreasing steps
dS = np.diff(S)
post = dS[t_pert:]
eps = 1e-5
monotonicity = float(np.mean(post >= -eps))

# recovery time: steps to return within 5% of pre-perturbation mean entropy
pre_mean = float(np.mean(S[max(0, t_pert-200):t_pert]))
target = pre_mean * 1.05
rec_idx = np.where(S[t_pert:] <= target)[0]
recovery_steps = int(rec_idx[0]) if len(rec_idx) else int(T - t_pert)

# spectral coherence: mean spectral lock over tail
tail_slice = slice(int(0.8*T), T)
spec_lock_tail = float(np.mean(R_spec[tail_slice]))

# drift in energy (relative to pre-pert mean)
E_pre = float(np.mean(E[max(0, t_pert-200):t_pert]))
E_post = float(np.mean(E[tail_slice]))
E_drift_rel = float(abs(E_post - E_pre) / (abs(E_pre) + 1e-16))

# smooth curves for plots
S_s = moving_avg(S, 41)
R_s = moving_avg(R_spec, 41)

# --- classification ---
# Tight pass: monotonic ≥ 0.9, recovery < 0.2T, tail lock ≥ 0.92, energy drift < 1e-3
# Marginal:   monotonic ≥ 0.75, recovery < 0.4T, tail lock ≥ 0.88, energy drift < 3e-3
if (monotonicity >= 0.90 and recovery_steps < 0.2*T and
    spec_lock_tail >= 0.92 and E_drift_rel < 1e-3):
    verdict = "✅ Stable propagation"
elif (monotonicity >= 0.75 and recovery_steps < 0.4*T and
      spec_lock_tail >= 0.88 and E_drift_rel < 3e-3):
    verdict = "⚠️ Marginal propagation"
else:
    verdict = "❌ Unstable propagation"

# --- save outputs ---
Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)

# Plots
plt.figure(figsize=(10,5))
plt.plot(t, S_s, lw=1.7, label="S(t) (smoothed)")
plt.axvline(t_pert*dt, color="red", ls="--", lw=1.2, label="perturb")
plt.title("E5 — Entropy Propagation & Recovery")
plt.xlabel("time"); plt.ylabel("entropy S"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_E5_EntropyPropagation.png", dpi=160)

plt.figure(figsize=(10,5))
plt.plot(t, R_s, lw=1.7, label="spectral lock (ref)")
plt.axhline(spec_lock_tail, color="gray", ls=":", label=f"tail mean={spec_lock_tail:.3f}")
plt.axvline(t_pert*dt, color="red", ls="--", lw=1.2)
plt.title("E5 — Spectral Coherence During Propagation")
plt.xlabel("time"); plt.ylabel("ρ_lock"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_E5_SpectralLock.png", dpi=160)

# JSON
out = {
    "N": N, "T": T, "dt": dt,
    "t_pert": t_pert, "block": block, "theta": theta,
    "noise_amp": noise_amp, "seed": seed,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "metrics": {
        "entropy_monotonicity": monotonicity,
        "recovery_steps": recovery_steps,
        "recovery_time": recovery_steps*dt,
        "spec_lock_tail": spec_lock_tail,
        "E_drift_rel": E_drift_rel,
        "S_pre_mean": pre_mean,
    },
    "classification": verdict,
    "files": {
        "entropy_plot": "PAEV_E5_EntropyPropagation.png",
        "spectral_plot": "PAEV_E5_SpectralLock.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = "backend/modules/knowledge/E5_entropy_propagation.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E5 — Entropy Propagation & Reversibility ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved → {save_path}")