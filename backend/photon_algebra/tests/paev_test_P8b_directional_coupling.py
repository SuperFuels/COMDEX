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
lag_window = 20  # ± time-step window for lag correlation analysis

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

# === Simulation ===
iA = iB = 0.0
dA_prev = dB_prev = 0.0
phi_diff_AB = np.zeros(T)

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

    phi_diff_AB[t] = np.abs(A["meta"][t] - B["meta"][t])

# === Lag-Correlation Analysis ===
def lag_corr(x, y, max_lag):
    corrs = []
    for lag in range(-max_lag, max_lag+1):
        if lag < 0:
            corrs.append(np.corrcoef(x[-lag:], y[:lag])[0,1])
        elif lag > 0:
            corrs.append(np.corrcoef(x[:-lag], y[lag:])[0,1])
        else:
            corrs.append(np.corrcoef(x, y)[0,1])
    return np.array(corrs)

tail_start = int(T*0.8)
corrs = lag_corr(A["meta"][tail_start:], B["meta"][tail_start:], lag_window)
lags = np.arange(-lag_window, lag_window+1)
lead_index = np.argmax(corrs)
lead_lag = lags[lead_index]
max_corr = corrs[lead_index]

direction = "A→B" if lead_lag > 0 else ("B→A" if lead_lag < 0 else "bidirectional")

# === Classification ===
if abs(lead_lag) <= 1:
    classification = "✅ Symmetric coherence (no lead)"
else:
    classification = f"⚡ Directional coherence: {direction}"

# === Plots ===
plt.figure(figsize=(9,5))
plt.plot(lags, corrs, color="blue")
plt.axvline(0, color="gray", linestyle="--")
plt.title("P8b — Cross-Attractor Lag Correlation (Predictive Directionality)")
plt.xlabel("Lag (steps)")
plt.ylabel("Cross-correlation")
plt.tight_layout()
plt.savefig("PAEV_P8b_LagCorrelation.png")
plt.close()

# === Output summary ===
print("=== P8b — Directional Predictive Coupling (Causality Layer) ===")
print(f"Peak corr={max_corr:.3f} at lag={lead_lag} ({direction}) → {classification}")

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
    "coupling_gain": coupling_gain,
    "predictive_lead": predictive_lead,
    "lag_window": lag_window,
    "lead_lag": int(lead_lag),
    "max_corr": float(max_corr),
    "direction": direction,
    "classification": classification,
    "files": {
        "lag_plot": "PAEV_P8b_LagCorrelation.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P8b_directional_coupling.json", "w") as f:
    json.dump(results, f, indent=2)