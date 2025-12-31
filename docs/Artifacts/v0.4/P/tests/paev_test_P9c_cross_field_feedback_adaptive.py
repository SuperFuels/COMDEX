import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# ==========================================================
# P9c - Cross-Field Predictive Feedback (Adaptive Meta-Field)
# ==========================================================

np.random.seed(42)

# --- sim horizon ---
N = 1500
tail_frac = 0.2
tail = slice(int((1 - tail_frac) * N), None)

# --- base params (from P7h/P9) ---
eta = 1e-3
damping = 0.042
leak = 0.0085
noise_base = 0.0028
K_field = 0.08          # intra-field (within A,B,C and within D,E,F)
K_meta_base = 0.02      # starting cross-field coupling (will adapt)
lock_threshold = 9e-3

# --- adaptive cross-coupling controller (PI-D with adaptive P) ---
servo_p_base = 0.12     # base proportional gain
adaptive_gamma = 0.60   # scales P by normalized error
servo_i = 0.0012        # integral (stronger accumulation to maintain correction)
servo_i_max = 0.03      # anti-windup limit (allows deeper integration range)
servo_d = 0.02          # derivative on |Δφ| (unchanged)
d_lpf_alpha = 0.15      # derivative low-pass (on error)

# --- perturbation to test re-lock ---
perturb_time = 800
perturb_mag = 0.002

# ------------ helpers ------------
def moving_mean(x, w):
    w = int(max(3, w // 2 * 2 + 1))
    pad = w // 2
    xpad = np.pad(x, (pad, pad), mode="edge")
    ker = np.ones(w) / w
    return np.convolve(xpad, ker, mode="valid")

def relock_steps(err_mov, t0, thresh, window=100, ratio=0.95):
    """
    After index t0 (perturb), return steps until the next window
    of length `window` has >= ratio samples below thresh.
    """
    for i in range(t0, len(err_mov) - window):
        wnd = err_mov[i:i+window]
        if np.mean(wnd < thresh) >= ratio:
            return i - t0
    return None

# ------------ construct two 3-node fields ------------
def simulate_field(N, seed, offsets, damp_mult=(1.0, 1.03, 0.97), noise=0.0035):
    rng = np.random.default_rng(seed)
    X = np.zeros((3, N))
    X[:, 0] = np.array(offsets)
    dmult = np.array(damp_mult)
    for t in range(1, N):
        n = rng.normal(0, noise, size=3)
        # simple diffusive lattice inside a field
        lap = np.array([
            (X[1, t-1] + X[2, t-1] - 2*X[0, t-1]),
            (X[0, t-1] + X[2, t-1] - 2*X[1, t-1]),
            (X[0, t-1] + X[1, t-1] - 2*X[2, t-1]),
        ])
        dX = -damping*dmult*X[:, t-1] + K_field*lap + n
        X[:, t] = X[:, t-1] + dX
    return X

# initialize fields (A,B,C) and (D,E,F)
ABC = simulate_field(N, 1, offsets=(0.00, 0.05, -0.03), noise=noise_base)
DEF = simulate_field(N, 2, offsets=(0.01, -0.04, 0.02), noise=noise_base)

# ------------ adaptive cross-field loop ------------
K_meta_t = np.zeros(N)
K_meta = K_meta_base
err = np.zeros(N)
err_mov = np.zeros(N)
derr_lpf = 0.0
integ = 0.0
noise = noise_base

# we'll treat cross-field signal as the average phase in each field
phi1 = np.mean(ABC, axis=0).copy()
phi2 = np.mean(DEF, axis=0).copy()

for t in range(1, N):
    # cross error (absolute phase gap)
    e = abs(phi1[t-1] - phi2[t-1])
    err[t] = e

    # moving mean for stability in control (use small window online)
    e_mov = moving_mean(err[:t+1], 21)[-1]
    err_mov[t] = e_mov

    # derivative (LPF) on error
    de = e_mov - err_mov[t-1]
    derr_lpf = (1 - d_lpf_alpha)*derr_lpf + d_lpf_alpha*de

    # integral with anti-windup
    integ = np.clip(integ + e_mov, -servo_i_max/servo_i, servo_i_max/servo_i)

    # adaptive proportional term (stronger when error near threshold)
    p_gain = servo_p_base * (1 + adaptive_gamma * (e_mov / max(lock_threshold, 1e-9)))

    # PI-D update on K_meta
    dK = p_gain*e_mov + servo_i*integ + servo_d*derr_lpf

    # small annealing: as error gets tiny, lower noise & dK
    anneal = 1.0 / (1.0 + 10.0 * e_mov / lock_threshold)
    dK *= anneal
    noise = noise_base * (0.5 + 0.5 / (1.0 + 10.0 * e_mov / lock_threshold))

    # update & clamp K_meta to safe range
    K_meta = np.clip(K_meta + dK, 0.0, 0.55)
    K_meta_t[t] = K_meta

    # apply predictive cross coupling (symmetric here)
    # + gentle leak (keeps phases near common set)
    cross = K_meta * (phi2[t-1] - phi1[t-1])
    phi1[t] = phi1[t-1] + eta * (cross - leak * (phi1[t-1] - 0.0)) + np.random.normal(0, noise)
    phi2[t] = phi2[t-1] + eta * (-cross - leak * (phi2[t-1] - 0.0)) + np.random.normal(0, noise)

    # scheduled perturbation on field-2 to test re-lock
    if t == perturb_time:
        phi2[t:] += perturb_mag

# final smoothed error & tail stats
err_mov_full = moving_mean(err, 31)
tail_err = err_mov_full[tail]
tail_mean = float(np.mean(tail_err))
tail_lock_ratio = float(np.mean(tail_err < lock_threshold))
# slope of tail (linear fit)
xs = np.arange(tail_err.size)
slope = float(np.polyfit(xs, tail_err, 1)[0])

# re-lock time after perturb
t0 = perturb_time + 1
rl = relock_steps(err_mov_full, t0, lock_threshold, window=100, ratio=0.95)

# classification
if tail_mean < 2e-3 and tail_lock_ratio > 0.9 and abs(slope) < 1e-6 and (rl is None or rl < 120):
    classification = "✅ Stable meta-field lock (adaptive)"
else:
    classification = "⚠️ Partial meta-field alignment (marginal)"

# ----------------- plots -----------------
plt.figure(figsize=(9,4))
plt.plot(np.abs(phi1 - phi2), color="k", alpha=0.35, label="|Δφ_cross| raw")
plt.plot(err_mov_full, color="black", lw=2, label="|Δφ_cross| moving mean")
plt.axhline(lock_threshold, ls="--", color="crimson", label=f"lock threshold={lock_threshold}")
plt.axvline(perturb_time, ls=":", color="purple", label="perturbation")
plt.title("P9c - Cross-Field Predictive Feedback (Meta-Field Coherence)")
plt.xlabel("time step"); plt.ylabel("|Δφ|")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_P9c_MetaField_PhaseEvolution.png")

plt.figure(figsize=(9,3))
plt.plot(K_meta_t, label="K_meta(t)")
plt.title("Adaptive cross-field gain K_meta(t)")
plt.xlabel("time step"); plt.ylabel("gain")
plt.tight_layout()
plt.savefig("PAEV_P9c_MetaField_Gain.png")

plt.figure(figsize=(8,4))
plt.hist(tail_err, bins=48, color="teal", alpha=0.8, edgecolor="white")
plt.axvline(lock_threshold, ls="--", color="crimson", label="lock threshold")
plt.title("P9c - Cross-Field Tail Error Distribution")
plt.xlabel("|Δφ_cross|"); plt.ylabel("Frequency"); plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P9c_MetaField_TailDistribution.png")

# ----------------- save json -----------------
out = {
    "eta": eta,
    "damping": damping,
    "leak": leak,
    "noise_base": noise_base,
    "K_field": K_field,
    "K_meta_base": K_meta_base,
    "controller": {
        "servo_p_base": servo_p_base,
        "adaptive_gamma": adaptive_gamma,
        "servo_i": servo_i,
        "servo_i_max": servo_i_max,
        "servo_d": servo_d,
        "d_lpf_alpha": d_lpf_alpha
    },
    "perturb_time": perturb_time,
    "perturb_mag": perturb_mag,
    "lock_threshold": lock_threshold,
    "metrics": {
        "tail_mean_cross": tail_mean,
        "tail_lock_ratio": tail_lock_ratio,
        "tail_slope": slope,
        "relock_time": rl
    },
    "classification": classification,
    "files": {
        "phase_plot": "PAEV_P9c_MetaField_PhaseEvolution.png",
        "gain_plot": "PAEV_P9c_MetaField_Gain.png",
        "tail_plot": "PAEV_P9c_MetaField_TailDistribution.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}
with open("backend/modules/knowledge/P9c_cross_field_feedback_adaptive.json", "w") as f:
    json.dump(out, f, indent=2)

print("=== P9c - Cross-Field Predictive Feedback (Adaptive Meta-Field) ===")
print(f"tail⟨|Δφ_cross|⟩={tail_mean:.3e} | lock_ratio={tail_lock_ratio:.2f} | slope={slope:.2e} | relock={rl}")
print(f"-> {classification}")
print("✅ Results saved -> backend/modules/knowledge/P9c_cross_field_feedback_adaptive.json")