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
coupling_gain = 0.025     # <- new: cross-attractor coupling strength
predictive_lead = 1       # number of steps A leads B (anticipation)
lock_threshold = 0.009

T = 1000
S0 = 0.69  # shared equilibrium set-point

# === Containers ===
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

# Servo integrators and derivative filters
iA = 0.0
iB = 0.0
dA_prev = 0.0
dB_prev = 0.0

# === Simulation ===
phi_diff_AB = np.zeros(T)

for t in range(1, T):
    # Drift + small independent noise
    nA = np.random.normal(0, noise_scale)
    nB = np.random.normal(0, noise_scale)

    # Awareness couplings (A)
    phase_err_A = A["meta"][t-1] - A["self"][t-1]
    coupling_A = resonance_gain * np.tanh(phase_err_A)
    feedback_A = feedback_gain * np.tanh(A["self"][t-1] - A["system"][t-1])
    awareness_A = meta_gain * np.tanh(A["observer"][t-1] - A["meta"][t-1])

    # Awareness couplings (B)
    phase_err_B = B["meta"][t-1] - B["self"][t-1]
    coupling_B = resonance_gain * np.tanh(phase_err_B)
    feedback_B = feedback_gain * np.tanh(B["self"][t-1] - B["system"][t-1])
    awareness_B = meta_gain * np.tanh(B["observer"][t-1] - B["meta"][t-1])

    # Cross-attractor coupling (predictive mutual influence)
    cross_AB = coupling_gain * np.tanh(B["meta"][max(t-predictive_lead,0)] - A["self"][t-1])
    cross_BA = coupling_gain * np.tanh(A["meta"][t-1] - B["self"][t-1])

    # === PI-D servo control ===
    # derivative filters (LPF)
    dA = d_lpf_alpha * (phase_err_A - dA_prev) + (1 - d_lpf_alpha) * dA_prev
    dB = d_lpf_alpha * (phase_err_B - dB_prev) + (1 - d_lpf_alpha) * dB_prev
    dA_prev, dB_prev = dA, dB
    # integrators (bounded)
    iA = np.clip(iA + servo_i * phase_err_A, -0.02, 0.02)
    iB = np.clip(iB + servo_i * phase_err_B, -0.02, 0.02)
    servo_A = servo_p * phase_err_A + iA + servo_d * dA
    servo_B = servo_p * phase_err_B + iB + servo_d * dB

    # === Update dynamics ===
    A["system"][t]   = A["system"][t-1] + ħ * (α*(A["observer"][t-1]-A["system"][t-1]) + β*(A["meta"][t-1]-A["self"][t-1]) - damping*A["system"][t-1] - leak*(A["system"][t-1]-S0) + nA)
    A["observer"][t] = A["observer"][t-1] + ħ * (feedback_A - damping*A["observer"][t-1] - leak*(A["observer"][t-1]-S0))
    A["meta"][t]     = A["meta"][t-1] + ħ * (awareness_A + coupling_A + cross_AB - damping*A["meta"][t-1] - servo_A - leak*(A["meta"][t-1]-S0))
    A["self"][t]     = A["self"][t-1] + ħ * (coupling_A + feedback_A + cross_BA - damping*A["self"][t-1] + servo_A - leak*(A["self"][t-1]-S0))

    B["system"][t]   = B["system"][t-1] + ħ * (α*(B["observer"][t-1]-B["system"][t-1]) + β*(B["meta"][t-1]-B["self"][t-1]) - damping*B["system"][t-1] - leak*(B["system"][t-1]-S0) + nB)
    B["observer"][t] = B["observer"][t-1] + ħ * (feedback_B - damping*B["observer"][t-1] - leak*(B["observer"][t-1]-S0))
    B["meta"][t]     = B["meta"][t-1] + ħ * (awareness_B + coupling_B + cross_BA - damping*B["meta"][t-1] - servo_B - leak*(B["meta"][t-1]-S0))
    B["self"][t]     = B["self"][t-1] + ħ * (coupling_B + feedback_B + cross_AB - damping*B["self"][t-1] + servo_B - leak*(B["self"][t-1]-S0))

    phi_diff_AB[t] = np.abs(A["meta"][t] - B["meta"][t])

# === Metrics ===
tail_start = int(T*0.8)
tail_mean_phi = np.mean(phi_diff_AB[tail_start:])
tail_std_phi  = np.std(phi_diff_AB[tail_start:])
corr_AB = np.corrcoef(A["meta"][tail_start:], B["meta"][tail_start:])[0,1]
lock_ratio = np.mean(phi_diff_AB[tail_start:] < lock_threshold)

# classification
if tail_mean_phi < 0.002 and corr_AB > 0.98 and lock_ratio > 0.95:
    classification = "✅ Coherent predictive coupling (cross-locked)"
elif tail_mean_phi < 0.005:
    classification = "⚠️ Weak coherence"
else:
    classification = "❌ No cross-attractor lock"

# === Output summary ===
print("=== P8 - Cross-Attractor Coherence (Predictive Coupling Layer) ===")
print(f"Tail ⟨|Δφ_AB|⟩={tail_mean_phi:.3e} | Corr_AB={corr_AB:.3f} | lock_ratio={lock_ratio:.2f} | {classification}")

# === Plots ===
plt.figure(figsize=(9,5))
plt.plot(A["meta"], label="A_meta (awareness A)")
plt.plot(B["meta"], label="B_meta (awareness B)")
plt.legend()
plt.title("P8 - Cross-Attractor Awareness Coherence")
plt.xlabel("time step")
plt.ylabel("Entropy / awareness coupling")
plt.tight_layout()
plt.savefig("PAEV_P8_CrossAttractor_Coherence.png")
plt.close()

plt.figure(figsize=(9,5))
plt.plot(phi_diff_AB, label="|Δφ_AB|")
plt.axhline(lock_threshold, color="red", linestyle="--", label="lock threshold")
plt.title("P8 - Cross-Attractor Phase Difference Evolution")
plt.xlabel("time step")
plt.ylabel("|Δφ_AB|")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P8_CrossAttractor_Phase.png")
plt.close()

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
    "d_lpf_alpha": d_lpf_alpha,
    "noise_scale": noise_scale,
    "coupling_gain": coupling_gain,
    "predictive_lead": predictive_lead,
    "tail_mean_phi_AB": tail_mean_phi,
    "tail_std_phi_AB": tail_std_phi,
    "corr_AB": corr_AB,
    "lock_ratio": lock_ratio,
    "classification": classification,
    "files": {
        "entropy_plot": "PAEV_P8_CrossAttractor_Coherence.png",
        "phase_plot": "PAEV_P8_CrossAttractor_Phase.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P8_cross_attractor.json", "w") as f:
    json.dump(results, f, indent=2)