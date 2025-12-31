import json, os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# -----------------------
# P7h - Sustained Awareness Attractor (Lock Tuning, PI-D + adaptive P)
# -----------------------

# Constants (kept for registry consistency)
ħ, G, Λ, α, β = 1e-3, 1e-5, 1e-6, 0.5, 0.2

# ===== Tunables =====
# System couplings
feedback_gain   = 0.18
meta_gain       = 0.12
awareness_gain  = 0.12
resonance_gain  = 0.07

# Energy terms
damping         = 0.042      # a touch lower to not fight the servo
leak            = 0.0085

# Servo (targeting |Δφ| <= lock_threshold)
lock_threshold  = 0.009
servo_p_base    = 0.10       # base P
adaptive_gamma  = 0.40       # P scales by 1 + gamma*(|Δφ|/thr - 1)+
servo_i         = 8e-4       # stronger integral to chew down bias slowly
servo_i_max     = 0.02       # anti-windup clamp for the integrator state
servo_d         = 0.020      # small derivative to quell micro-oscillations
d_lpf_alpha     = 0.15       # low-pass for derivative

# Bias shaping & noise (small, to test pure servo ability)
bias_amp        = 0.0023
tau_bias        = 360.0
noise_scale     = 0.0035

# Analysis windows
T               = 800
tail_frac       = 0.2
mov_w           = 31         # moving-average window for the phase plot
history_file    = "backend/modules/knowledge/P7_lock_history.json"

# ===== Initialization =====
rng = np.random.default_rng(42)
S_system   = np.zeros(T)
S_observer = np.zeros(T)
S_meta     = np.zeros(T)
S_self     = np.zeros(T)
phi_abs    = np.zeros(T)

S_system[0], S_observer[0], S_meta[0], S_self[0] = 0.70, 0.69, 0.68, 0.67
S0 = 0.69

# Servo state
i_state = 0.0
prev_phi = abs(S_meta[0] - S_self[0])
d_state = prev_phi  # for LPF derivative seed

# ===== Evolution =====
for t in range(1, T):
    # External bias + noise
    bias = bias_amp * np.exp(-t / tau_bias)
    noise = rng.normal(0.0, noise_scale)

    # System-level exchange (small)
    dS = α*(S_observer[t-1] - S_system[t-1]) + β*(S_meta[t-1] - S_self[t-1]) + noise + bias

    # Nonlinear couplings
    coupling  = resonance_gain * np.tanh(S_meta[t-1] - S_self[t-1])
    feedback  = feedback_gain  * np.tanh(S_self[t-1] - S_system[t-1])
    awareness = meta_gain      * np.tanh(S_observer[t-1] - S_meta[t-1])

    # Phase error and servo (PI-D with adaptive P and anti-windup)
    phi = S_meta[t-1] - S_self[t-1]
    abs_phi = abs(phi)

    # Adaptive P only bites outside the threshold
    over = max(abs_phi/lock_threshold - 1.0, 0.0)
    servo_p = servo_p_base * (1.0 + adaptive_gamma * over)

    # Integral (track sign of phi; clamp)
    i_state += servo_i * np.sign(phi)
    i_state = np.clip(i_state, -servo_i_max, servo_i_max)

    # Derivative on |phi| with light LPF to reduce noise kick
    d_raw = abs_phi - prev_phi
    d_state = (1 - d_lpf_alpha)*d_state + d_lpf_alpha*d_raw

    # Servo action: push S_meta and S_self toward each other
    servo_term = (servo_p * np.sign(-phi)) + i_state + (servo_d * np.sign(-d_state))
    prev_phi = abs_phi

    # Core updates with damping & leak toward S0
    S_system[t]   = S_system[t-1]   + ħ*( dS - damping*S_system[t-1]   - leak*(S_system[t-1]   - S0) )
    S_observer[t] = S_observer[t-1] + ħ*( feedback - damping*S_observer[t-1] - leak*(S_observer[t-1] - S0) )
    S_meta[t]     = S_meta[t-1]     + ħ*( awareness + coupling - damping*S_meta[t-1]
                                         - leak*(S_meta[t-1] - S0) + servo_term )
    S_self[t]     = S_self[t-1]     + ħ*( coupling + feedback - damping*S_self[t-1]
                                         - leak*(S_self[t-1] - S0) - servo_term )

    phi_abs[t] = abs(S_meta[t] - S_self[t])

# ===== Metrics & lock diagnostics =====
def moving_mean(x, w):
    if w <= 1:
        return x.copy()
    box = np.ones(w)/w
    return np.convolve(x, box, mode="same")

tail_start = int((1.0 - tail_frac)*T)
tail_phi   = phi_abs[tail_start:]
tail_mean  = float(np.mean(tail_phi))
slope      = float(np.polyfit(np.arange(len(tail_phi)), tail_phi, 1)[0])
corr       = float(np.corrcoef(S_meta, S_self)[0,1])
std_phi    = float(np.std(tail_phi))
lock_band  = phi_abs <= lock_threshold
lock_ratio = float(np.mean(lock_band[tail_start:]))  # % of tail samples within threshold

# Weighted lock score (0..1-ish)
lock_score = float(
    (0.40 * (1.0 - min(tail_mean/lock_threshold, 2.0)/2.0)) +
    (0.25 * max(0.0, 1.0 - abs(slope) / 1e-5)) +
    (0.20 * max(0.0, corr)) +
    (0.15 * lock_ratio)
)

# Classification
if (tail_mean < lock_threshold) and (lock_ratio > 0.5) and (abs(slope) < 5e-6):
    classification = "✅ Stable awareness attractor (locked)"
elif (tail_mean < 0.012) and (lock_ratio > 0.2):
    classification = "🟡 Near-lock (tighten servo)"
else:
    classification = "⚠️ Marginal attractor"

# ===== History (for continuous improvement tracking) =====
os.makedirs("backend/modules/knowledge", exist_ok=True)
prev_tail = None
delta_tail = None
try:
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            hist = json.load(f)
        prev_tail = hist.get("last_tail_mean")
except Exception:
    prev_tail = None

if prev_tail is not None:
    delta_tail = float(prev_tail - tail_mean)

with open(history_file, "w") as f:
    json.dump({"last_tail_mean": tail_mean,
               "last_run": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")}, f, indent=2)

# ===== Plots =====
# Entropy trajectories
plt.figure(figsize=(10,5))
plt.plot(S_system,   label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_meta,     label="S_meta (awareness)")
plt.plot(S_self,     label="S_self (feedback)")
plt.title("P7h - Sustained Awareness Attractor (Lock Tuning, PI-D + adaptive P)")
plt.xlabel("time step"); plt.ylabel("Entropy / awareness coupling")
plt.legend(); plt.tight_layout()
plt.savefig("backend/modules/knowledge/PAEV_P7h_LockTuning_Entropy.png", dpi=130)
plt.close()

# Phase error with moving mean & tail window
phi_ma = moving_mean(phi_abs, mov_w)
plt.figure(figsize=(10,5))
plt.plot(phi_abs, alpha=0.35, label="|Δφ| raw")
plt.plot(phi_ma,  lw=2.0,     label=f"|Δφ| moving mean (w={mov_w})")
plt.axhline(lock_threshold, ls="--", color="crimson", alpha=0.8, label=f"lock threshold={lock_threshold:g}")
plt.axvspan(tail_start, T-1, color="k", alpha=0.06, label="evaluation tail")
plt.title("P7h - Phase Error Evolution (Lock Tuning)")
plt.xlabel("time step"); plt.ylabel("|Δφ|")
plt.legend(); plt.tight_layout()
plt.savefig("backend/modules/knowledge/PAEV_P7h_LockTuning_Phase.png", dpi=130)
plt.close()

# ===== Save JSON summary =====
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain, "meta_gain": meta_gain,
    "awareness_gain": awareness_gain, "resonance_gain": resonance_gain,
    "damping": damping, "leak": leak,
    "servo_p_base": servo_p_base, "adaptive_gamma": adaptive_gamma,
    "servo_i": servo_i, "servo_i_max": servo_i_max,
    "servo_d": servo_d, "d_lpf_alpha": d_lpf_alpha,
    "bias_amp": bias_amp, "tau_bias": tau_bias,
    "noise_scale": noise_scale,
    "lock_threshold": lock_threshold, "mov_w": mov_w, "tail_frac": tail_frac,
    "mean_phase_diff": float(np.mean(phi_abs)),
    "tail_mean_phase_diff": tail_mean,
    "corr_meta_self": corr,
    "std_phase_tail": std_phi,
    "phase_slope_tail": slope,
    "lock_ratio_tail": lock_ratio,
    "lock_score": lock_score,
    "classification": classification,
    "previous_tail_mean_phase_diff": prev_tail,
    "delta_tail_improvement": delta_tail,
    "files": {
        "entropy_plot": "PAEV_P7h_LockTuning_Entropy.png",
        "phase_plot": "PAEV_P7h_LockTuning_Phase.png",
        "history": "P7_lock_history.json"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

out_json = "backend/modules/knowledge/P7h_lock_tuning.json"
with open(out_json, "w") as f:
    json.dump(summary, f, indent=2)

# ===== Console report =====
print("=== P7h - Sustained Awareness Attractor (Lock Tuning, PI-D + adaptive P) ===")
print(f"tail⟨|Δφ|⟩={tail_mean:.3e} "
      f"| corr={corr:.3f} | slope={slope:.2e} | lock_ratio={lock_ratio:.2f} | score={lock_score:.2f} -> {classification}")
print(f"Δtail (improvement vs last) = {delta_tail:+.3e}" if delta_tail is not None else "Δtail (first run) = N/A")
print(f"✅ Results saved -> {out_json}")