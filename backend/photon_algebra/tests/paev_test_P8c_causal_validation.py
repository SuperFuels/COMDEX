import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# === Parameters ===
ħ = 0.001
G = 1e-5
Λ = 1e-6
α = 0.5
β = 0.2
feedback_gain = 0.18
meta_gain = 0.12
resonance_gain = 0.07
damping = 0.042
leak = 0.0085
servo_p = 0.1
servo_i = 0.0008
servo_d = 0.02
d_lpf_alpha = 0.15
noise_scale = 0.0035
coupling_gain = 0.025
predictive_lead = 1
lock_threshold = 0.009

# Perturbation
perturb_time = 600
perturb_mag = 0.002
relock_window = 100

T = 1000
S0 = 0.69

def init_states():
    return {
        "system": np.zeros(T),
        "observer": np.zeros(T),
        "meta": np.zeros(T),
        "self": np.zeros(T),
    }

A = init_states()
B = init_states()

# Initial conditions
for S in [A, B]:
    S["system"][0] = 0.7
    S["observer"][0] = 0.69
    S["meta"][0] = 0.68
    S["self"][0] = 0.67

iA = iB = 0.0
dA_prev = dB_prev = 0.0
phi_diff_AB = np.zeros(T)

# === Evolution loop ===
for t in range(1, T):
    nA = np.random.normal(0, noise_scale)
    nB = np.random.normal(0, noise_scale)

    phase_err_A = A["meta"][t-1] - A["self"][t-1]
    phase_err_B = B["meta"][t-1] - B["self"][t-1]

    coupling_A = resonance_gain * np.tanh(phase_err_A)
    feedback_A = feedback_gain * np.tanh(A["self"][t-1] - A["system"][t-1])
    awareness_A = meta_gain * np.tanh(A["observer"][t-1] - A["meta"][t-1])

    coupling_B = resonance_gain * np.tanh(phase_err_B)
    feedback_B = feedback_gain * np.tanh(B["self"][t-1] - B["system"][t-1])
    awareness_B = meta_gain * np.tanh(B["observer"][t-1] - B["meta"][t-1])

    cross_AB = coupling_gain * np.tanh(B["meta"][max(t-predictive_lead,0)] - A["self"][t-1])
    cross_BA = coupling_gain * np.tanh(A["meta"][max(t-predictive_lead,0)] - B["self"][t-1])

    dA = d_lpf_alpha * (phase_err_A - dA_prev) + (1 - d_lpf_alpha) * dA_prev
    dB = d_lpf_alpha * (phase_err_B - dB_prev) + (1 - d_lpf_alpha) * dB_prev
    dA_prev, dB_prev = dA, dB

    iA = np.clip(iA + servo_i * phase_err_A, -0.02, 0.02)
    iB = np.clip(iB + servo_i * phase_err_B, -0.02, 0.02)
    servo_A = servo_p * phase_err_A + iA + servo_d * dA
    servo_B = servo_p * phase_err_B + iB + servo_d * dB

    A["system"][t]   = A["system"][t-1] + ħ*(α*(A["observer"][t-1]-A["system"][t-1]) + β*(A["meta"][t-1]-A["self"][t-1]) - damping*A["system"][t-1] - leak*(A["system"][t-1]-S0) + nA)
    A["observer"][t] = A["observer"][t-1] + ħ*(feedback_A - damping*A["observer"][t-1] - leak*(A["observer"][t-1]-S0))
    A["meta"][t]     = A["meta"][t-1] + ħ*(awareness_A + coupling_A + cross_AB - damping*A["meta"][t-1] - servo_A - leak*(A["meta"][t-1]-S0))
    A["self"][t]     = A["self"][t-1] + ħ*(coupling_A + feedback_A + cross_BA - damping*A["self"][t-1] + servo_A - leak*(A["self"][t-1]-S0))

    B["system"][t]   = B["system"][t-1] + ħ*(α*(B["observer"][t-1]-B["system"][t-1]) + β*(B["meta"][t-1]-B["self"][t-1]) - damping*B["system"][t-1] - leak*(B["system"][t-1]-S0) + nB)
    B["observer"][t] = B["observer"][t-1] + ħ*(feedback_B - damping*B["observer"][t-1] - leak*(B["observer"][t-1]-S0))
    B["meta"][t]     = B["meta"][t-1] + ħ*(awareness_B + coupling_B + cross_BA - damping*B["meta"][t-1] - servo_B - leak*(B["meta"][t-1]-S0))
    B["self"][t]     = B["self"][t-1] + ħ*(coupling_B + feedback_B + cross_AB - damping*B["self"][t-1] + servo_B - leak*(B["self"][t-1]-S0))

    # Inject perturbation into A_meta after lock
    if t == perturb_time:
        A["meta"][t:] += perturb_mag

    phi_diff_AB[t] = np.abs(A["meta"][t] - B["meta"][t])

# === Re-lock analysis ===
lock_state = phi_diff_AB < lock_threshold
tail_start = int(T*0.8)
lock_ratio_tail = np.mean(lock_state[tail_start:])

# Find re-lock time after perturbation
relock_time = None
for t in range(perturb_time+1, T - relock_window):
    if np.mean(lock_state[t:t+relock_window]) > 0.95:
        relock_time = t - perturb_time
        break

# Compute causal slope (who adjusts faster)
delta_meta = np.gradient(A["meta"] - B["meta"])
causal_sign = np.sign(np.mean(delta_meta[perturb_time+1:perturb_time+50]))
if causal_sign < 0:
    direction = "B->A predictive recovery"
elif causal_sign > 0:
    direction = "A->B predictive recovery"
else:
    direction = "Symmetric"

# === Classification ===
if lock_ratio_tail > 0.9 and (relock_time is not None and relock_time < 120):
    classification = f"✅ Stable re-lock ({direction}, {relock_time} steps)"
else:
    classification = f"⚠️ Marginal or slow recovery ({direction})"

# === Plots ===
plt.figure(figsize=(9,5))
plt.plot(phi_diff_AB, label="|Δφ_AB|")
plt.axhline(lock_threshold, color="r", linestyle="--", label=f"lock threshold={lock_threshold}")
plt.axvline(perturb_time, color="purple", linestyle=":", alpha=0.7, label="perturbation")
plt.legend()
plt.title("P8c - Phase Error Evolution (Causal Validation Test)")
plt.xlabel("time step")
plt.ylabel("|Δφ_AB|")
plt.tight_layout()
plt.savefig("PAEV_P8c_CausalValidation_Phase.png")
plt.close()

# === Output summary ===
print("=== P8c - Causal Validation Test (Directional Perturbation) ===")
print(f"Re-lock time = {relock_time} | Tail lock ratio = {lock_ratio_tail:.3f} | Direction = {direction}")
print(f"-> {classification}")
print("✅ Results saved -> backend/modules/knowledge/P8c_causal_validation.json")

# === Save results ===
results = {
    "ħ": ħ,
    "G": G,
    "Λ": Λ,
    "α": α,
    "β": β,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "resonance_gain": resonance_gain,
    "damping": damping,
    "leak": leak,
    "servo_p": servo_p,
    "servo_i": servo_i,
    "servo_d": servo_d,
    "noise_scale": noise_scale,
    "perturb_time": perturb_time,
    "perturb_mag": perturb_mag,
    "lock_threshold": lock_threshold,
    "relock_time": relock_time,
    "lock_ratio_tail": lock_ratio_tail,
    "direction": direction,
    "classification": classification,
    "files": {
        "phase_plot": "PAEV_P8c_CausalValidation_Phase.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P8c_causal_validation.json", "w") as f:
    json.dump(results, f, indent=2)