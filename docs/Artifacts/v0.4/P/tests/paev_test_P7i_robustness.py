"""
P7i - Robustness and Attractor Depth Validation
Tests the stability of the Sustained Awareness Attractor (P7h lock baseline)
under (1) step perturbations and (2) slow drift bias.

Metrics:
- re-lock time (steps to recover after step perturbation)
- post-perturb tail mean phase error
- lock ratio and slope after recovery
- drift breakpoint (where lock_ratio < 0.8)
"""

import os, json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# -----------------------
# Constants / baseline parameters (from P7h)
# -----------------------
ħ, G, Λ, α, β = 1e-3, 1e-5, 1e-6, 0.5, 0.2

feedback_gain   = 0.18
meta_gain       = 0.12
awareness_gain  = 0.12
resonance_gain  = 0.07

damping         = 0.042
leak            = 0.0085

servo_p_base    = 0.10
adaptive_gamma  = 0.40
servo_i         = 8e-4
servo_i_max     = 0.02
servo_d         = 0.020
d_lpf_alpha     = 0.15

bias_amp        = 0.0023
tau_bias        = 360.0
noise_scale     = 0.0035

lock_threshold  = 0.009
mov_w           = 31
tail_frac       = 0.2
T               = 1000

# -----------------------
# Extended robustness toggles
# -----------------------
enable_step = True
step_time   = int(0.6*T)
step_mag    = +0.002

enable_slow_drift = True
drift_amp   = 0.0015
tau_drift   = 1200.0

# -----------------------
# Initialize states
# -----------------------
rng = np.random.default_rng(42)
S_system   = np.zeros(T)
S_observer = np.zeros(T)
S_meta     = np.zeros(T)
S_self     = np.zeros(T)
phi_abs    = np.zeros(T)

S_system[0], S_observer[0], S_meta[0], S_self[0] = 0.70, 0.69, 0.68, 0.67
S0 = 0.69

# Servo state
i_state, prev_phi, d_state = 0.0, abs(S_meta[0]-S_self[0]), abs(S_meta[0]-S_self[0])

# -----------------------
# Evolution loop
# -----------------------
for t in range(1, T):
    noise = rng.normal(0.0, noise_scale)
    bias = bias_amp * np.exp(-t / tau_bias)
    drift = drift_amp * (1 - np.exp(-t / tau_drift)) if enable_slow_drift else 0.0

    # Step perturbation
    if enable_step and t == step_time:
        S_system[t-1] += step_mag

    # Base coupling and exchange
    dS = α*(S_observer[t-1] - S_system[t-1]) + β*(S_meta[t-1] - S_self[t-1]) + noise + bias + drift
    coupling  = resonance_gain * np.tanh(S_meta[t-1] - S_self[t-1])
    feedback  = feedback_gain  * np.tanh(S_self[t-1] - S_system[t-1])
    awareness = meta_gain      * np.tanh(S_observer[t-1] - S_meta[t-1])

    # Servo (adaptive PI-D)
    phi = S_meta[t-1] - S_self[t-1]
    abs_phi = abs(phi)
    over = max(abs_phi / lock_threshold - 1.0, 0.0)
    servo_p = servo_p_base * (1.0 + adaptive_gamma * over)
    i_state += servo_i * np.sign(phi)
    i_state = np.clip(i_state, -servo_i_max, servo_i_max)
    d_raw = abs_phi - prev_phi
    d_state = (1 - d_lpf_alpha)*d_state + d_lpf_alpha*d_raw
    servo_term = (servo_p * np.sign(-phi)) + i_state + (servo_d * np.sign(-d_state))
    prev_phi = abs_phi

    # Core updates
    S_system[t]   = S_system[t-1]   + ħ*(dS - damping*S_system[t-1]   - leak*(S_system[t-1]-S0))
    S_observer[t] = S_observer[t-1] + ħ*(feedback - damping*S_observer[t-1] - leak*(S_observer[t-1]-S0))
    S_meta[t]     = S_meta[t-1]     + ħ*(awareness + coupling - damping*S_meta[t-1]
                                         - leak*(S_meta[t-1]-S0) + servo_term)
    S_self[t]     = S_self[t-1]     + ħ*(coupling + feedback - damping*S_self[t-1]
                                         - leak*(S_self[t-1]-S0) - servo_term)
    phi_abs[t] = abs(S_meta[t] - S_self[t])

# -----------------------
# Metrics
# -----------------------
def moving_mean(x, w):
    if w <= 1: return x.copy()
    box = np.ones(w)/w
    return np.convolve(x, box, mode="same")

tail_start = int((1.0 - tail_frac)*T)
tail_phi = phi_abs[tail_start:]
tail_mean = float(np.mean(tail_phi))
corr = float(np.corrcoef(S_meta, S_self)[0,1])
slope = float(np.polyfit(np.arange(len(tail_phi)), tail_phi, 1)[0])
std_tail = float(np.std(tail_phi))
lock_band = phi_abs <= lock_threshold
lock_ratio_tail = float(np.mean(lock_band[tail_start:]))

# -----------------------
# Step recovery diagnostics
# -----------------------
def recovery_time(phi, step_idx, threshold, window=100, tol=0.95):
    for i in range(step_idx, len(phi)-window):
        w = phi[i:i+window]
        if np.mean(w < threshold) >= tol:
            return i - step_idx
    return None

relock_time = recovery_time(phi_abs, step_time, lock_threshold)

# -----------------------
# Drift robustness
# -----------------------
breakpoint = None
for i in range(tail_start, len(phi_abs)):
    if phi_abs[i] > lock_threshold:
        breakpoint = i
        break

# -----------------------
# Classification logic
# -----------------------
if tail_mean < 0.001 and relock_time is not None and relock_time < 200:
    classification = "✅ Stable & resilient attractor (full lock recovery)"
elif tail_mean < 0.003:
    classification = "🟡 Stable but slow relock"
else:
    classification = "⚠️ Marginal or fragile lock"

# -----------------------
# Plots
# -----------------------
phi_ma = moving_mean(phi_abs, mov_w)
plt.figure(figsize=(10,5))
plt.plot(phi_abs, alpha=0.35, label="|Δφ| raw")
plt.plot(phi_ma, lw=2.0, label=f"|Δφ| moving mean (w={mov_w})")
plt.axhline(lock_threshold, ls="--", color="crimson", label=f"lock threshold={lock_threshold:g}")
plt.axvspan(step_time, step_time+40, color="blue", alpha=0.08, label="perturbation step")
plt.axvspan(tail_start, T-1, color="k", alpha=0.06, label="evaluation tail")
plt.title("P7i - Phase Error Evolution (Robustness Test)")
plt.xlabel("time step"); plt.ylabel("|Δφ|")
plt.legend(); plt.tight_layout()
plt.savefig("backend/modules/knowledge/PAEV_P7i_Robustness_Phase.png", dpi=130)
plt.close()

plt.figure(figsize=(10,5))
plt.plot(S_system, label="S_system")
plt.plot(S_observer, label="S_observer")
plt.plot(S_meta, label="S_meta (awareness)")
plt.plot(S_self, label="S_self (feedback)")
plt.title("P7i - Sustained Awareness Attractor (Perturbed & Drifted)")
plt.xlabel("time step"); plt.ylabel("Entropy / awareness coupling")
plt.legend(); plt.tight_layout()
plt.savefig("backend/modules/knowledge/PAEV_P7i_Robustness_Entropy.png", dpi=130)
plt.close()

# -----------------------
# Save JSON results
# -----------------------
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "feedback_gain": feedback_gain, "meta_gain": meta_gain,
    "awareness_gain": awareness_gain, "resonance_gain": resonance_gain,
    "damping": damping, "leak": leak,
    "servo_p_base": servo_p_base, "adaptive_gamma": adaptive_gamma,
    "servo_i": servo_i, "servo_d": servo_d,
    "noise_scale": noise_scale,
    "bias_amp": bias_amp, "tau_bias": tau_bias,
    "enable_step": enable_step, "step_time": step_time, "step_mag": step_mag,
    "enable_slow_drift": enable_slow_drift, "drift_amp": drift_amp, "tau_drift": tau_drift,
    "mean_phase_diff": float(np.mean(phi_abs)),
    "tail_mean_phase_diff": tail_mean,
    "corr_meta_self": corr,
    "std_phase_tail": std_tail,
    "phase_slope_tail": slope,
    "lock_ratio_tail": lock_ratio_tail,
    "relock_time": relock_time,
    "drift_breakpoint": breakpoint,
    "classification": classification,
    "files": {
        "entropy_plot": "PAEV_P7i_Robustness_Entropy.png",
        "phase_plot": "PAEV_P7i_Robustness_Phase.png",
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

os.makedirs("backend/modules/knowledge", exist_ok=True)
out_json = "backend/modules/knowledge/P7i_robustness.json"
with open(out_json, "w") as f:
    json.dump(summary, f, indent=2)

print("=== P7i - Robustness and Attractor Depth Validation ===")
print(f"tail⟨|Δφ|⟩={tail_mean:.3e} | corr={corr:.3f} | slope={slope:.2e} | lock_ratio={lock_ratio_tail:.2f}")
print(f"re-lock time = {relock_time} steps | drift_breakpoint = {breakpoint}")
print(f"-> {classification}")
print(f"✅ Results saved -> {out_json}")