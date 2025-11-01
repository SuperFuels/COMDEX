import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# ==========================================================
# P9 - Predictive Field Coupling (Multi-Attractor Coherence)
# ==========================================================

np.random.seed(42)
N = 1000  # simulation steps

# --- base parameters (from P8 stable configs) ---
η = 0.001
G = 1e-5
Λ = 1e-6
α, β = 0.5, 0.2
feedback_gain = 0.18
meta_gain = 0.12
resonance_gain = 0.07
damping = 0.042
leak = 0.0085
noise_scale = 0.0035

# --- field coupling parameters ---
K_field = 0.08   # global coupling gain
lock_threshold = 0.009

# --- initialize 3 attractors (A, B, C) ---
φ_A = np.zeros(N)
φ_B = np.zeros(N)
φ_C = np.zeros(N)

φ_A[0], φ_B[0], φ_C[0] = 0.0, 0.05, -0.03

# Slight heterogeneity in parameters
damping_A = damping * 1.00
damping_B = damping * 1.03
damping_C = damping * 0.97

# --- simulation loop ---
for t in range(1, N):
    noise_A = np.random.normal(0, noise_scale)
    noise_B = np.random.normal(0, noise_scale)
    noise_C = np.random.normal(0, noise_scale)

    # local phase dynamics + coupling
    dφ_A = -damping_A * φ_A[t-1] + K_field * (φ_B[t-1] + φ_C[t-1] - 2 * φ_A[t-1]) + noise_A
    dφ_B = -damping_B * φ_B[t-1] + K_field * (φ_A[t-1] + φ_C[t-1] - 2 * φ_B[t-1]) + noise_B
    dφ_C = -damping_C * φ_C[t-1] + K_field * (φ_A[t-1] + φ_B[t-1] - 2 * φ_C[t-1]) + noise_C

    φ_A[t] = φ_A[t-1] + dφ_A
    φ_B[t] = φ_B[t-1] + dφ_B
    φ_C[t] = φ_C[t-1] + dφ_C

# --- compute field metrics ---
Δ_AB = np.abs(φ_A - φ_B)
Δ_BC = np.abs(φ_B - φ_C)
Δ_AC = np.abs(φ_A - φ_C)

tail = slice(int(0.8 * N), None)

tail_mean_field_error = np.mean([
    np.mean(Δ_AB[tail]),
    np.mean(Δ_BC[tail]),
    np.mean(Δ_AC[tail])
])

lock_ratio = np.mean(
    (Δ_AB[tail] < lock_threshold) &
    (Δ_BC[tail] < lock_threshold) &
    (Δ_AC[tail] < lock_threshold)
)

# Pairwise correlations
corr_AB = np.corrcoef(φ_A[tail], φ_B[tail])[0, 1]
corr_BC = np.corrcoef(φ_B[tail], φ_C[tail])[0, 1]
corr_AC = np.corrcoef(φ_A[tail], φ_C[tail])[0, 1]
mean_corr = np.mean([corr_AB, corr_BC, corr_AC])

# --- determine strongest predictive direction safely ---
lags = np.arange(-10, 11)

def lagged_corr(x, y, lag):
    if lag > 0:
        return np.corrcoef(x[lag:], y[:-lag])[0, 1]
    elif lag < 0:
        return np.corrcoef(x[:lag], y[-lag:])[0, 1]
    else:
        return np.corrcoef(x, y)[0, 1]

def safe_xcorr(x, y, lags):
    vals = []
    for l in lags:
        try:
            val = lagged_corr(x, y, l)
        except Exception:
            val = np.nan
        vals.append(val)
    return np.nan_to_num(vals, nan=0.0)

xcorrs_AB = safe_xcorr(φ_A, φ_B, lags)
xcorrs_BC = safe_xcorr(φ_B, φ_C, lags)
xcorrs_AC = safe_xcorr(φ_A, φ_C, lags)

lag_AB = lags[np.argmax(xcorrs_AB)]
lag_BC = lags[np.argmax(xcorrs_BC)]
lag_AC = lags[np.argmax(xcorrs_AC)]

def interpret(lag):
    if lag < 0: return "-> forward"
    elif lag > 0: return "<- reverse"
    else: return "↔ synchronous"

direction_summary = {
    "A↔B": interpret(lag_AB),
    "B↔C": interpret(lag_BC),
    "A↔C": interpret(lag_AC)
}

# --- classification logic ---
if (tail_mean_field_error < 2e-3 and lock_ratio > 0.9 and mean_corr > 0.97):
    classification = "✅ Stable predictive field (multi-attractor coherence)"
else:
    classification = "⚠️ Partial field coherence (marginal stability)"

# ==========================================================
# --- Plot 1: Phase Error Evolution ---
plt.figure(figsize=(8, 4))
plt.plot(Δ_AB, label="|Δφ_AB|")
plt.plot(Δ_BC, label="|Δφ_BC|")
plt.plot(Δ_AC, label="|Δφ_AC|")
plt.axhline(lock_threshold, color="r", linestyle="--", label=f"lock threshold={lock_threshold}")
plt.title("P9 - Field Phase Difference Evolution")
plt.xlabel("time step")
plt.ylabel("|Δφ|")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P9_Field_PhaseEvolution.png")

# --- Plot 2: Pairwise Correlations ---
plt.figure(figsize=(6, 4))
pairs = ["A↔B", "B↔C", "A↔C"]
corrs = [corr_AB, corr_BC, corr_AC]
plt.bar(pairs, corrs, color="mediumseagreen")
plt.ylim(0, 1)
plt.title("P9 - Pairwise Correlations (Field Coherence)")
plt.ylabel("Correlation")
plt.tight_layout()
plt.savefig("PAEV_P9_Field_PairwiseCorrelations.png")

# ==========================================================
# --- Save Results JSON ---
result = {
    "η": η,
    "G": G,
    "Λ": Λ,
    "α": α,
    "β": β,
    "feedback_gain": feedback_gain,
    "meta_gain": meta_gain,
    "resonance_gain": resonance_gain,
    "damping": damping,
    "leak": leak,
    "noise_scale": noise_scale,
    "K_field": K_field,
    "tail_mean_field_error": float(tail_mean_field_error),
    "lock_ratio": float(lock_ratio),
    "corr_AB": float(corr_AB),
    "corr_BC": float(corr_BC),
    "corr_AC": float(corr_AC),
    "mean_corr": float(mean_corr),
    "lag_AB": int(lag_AB),
    "lag_BC": int(lag_BC),
    "lag_AC": int(lag_AC),
    "direction_summary": direction_summary,
    "classification": classification,
    "files": {
        "phase_plot": "PAEV_P9_Field_PhaseEvolution.png",
        "corr_plot": "PAEV_P9_Field_PairwiseCorrelations.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P9_predictive_field.json", "w") as f:
    json.dump(result, f, indent=2)

print("=== P9 - Predictive Field Coupling (Multi-Attractor Coherence) ===")
print(f"Tail ⟨|Δφ_field|⟩={tail_mean_field_error:.3e} | Mean Corr={mean_corr:.3f} | Lock={lock_ratio:.2f}")
print(f"Direction Summary: {direction_summary}")
print(f"-> {classification}")
print("✅ Results saved -> backend/modules/knowledge/P9_predictive_field.json")