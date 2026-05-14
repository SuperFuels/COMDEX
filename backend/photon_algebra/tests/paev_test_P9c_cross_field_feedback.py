import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# ==========================================================
# P9c - Cross-Field Predictive Feedback (Meta-Field Coherence)
# ==========================================================

np.random.seed(42)
N = 1500  # extended simulation time

# --- base parameters (from P9b stable regime) ---
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

K_field = 0.08      # intra-field coupling
K_meta = 0.035      # inter-field (meta) coupling
lock_threshold = 0.009

# --- perturbation setup ---
perturb_time = 800
perturb_mag = 0.002

# --- initialize attractors (6 total) ---
φ_A = np.zeros(N)
φ_B = np.zeros(N)
φ_C = np.zeros(N)
φ_D = np.zeros(N)
φ_E = np.zeros(N)
φ_F = np.zeros(N)

φ_A[0], φ_B[0], φ_C[0] = 0.0, 0.05, -0.03
φ_D[0], φ_E[0], φ_F[0] = 0.02, -0.04, 0.03

damping_A = damping
damping_B = damping * 1.03
damping_C = damping * 0.97
damping_D = damping * 1.01
damping_E = damping * 0.99
damping_F = damping * 1.02

# ==========================================================
# --- Simulation Loop ---
# ==========================================================

for t in range(1, N):
    noise = lambda: np.random.normal(0, noise_scale)

    # intra-field coupling
    def field_dynamics(φ1, φ2, φ3, damping_local, meta_input):
        return -damping_local * φ1 + K_field * (φ2 + φ3 - 2 * φ1) + noise() + meta_input

    # meta-field coupling (field-level mean difference)
    mean_field1 = np.mean([φ_A[t-1], φ_B[t-1], φ_C[t-1]])
    mean_field2 = np.mean([φ_D[t-1], φ_E[t-1], φ_F[t-1]])
    meta_term_1 = K_meta * (mean_field2 - mean_field1)
    meta_term_2 = K_meta * (mean_field1 - mean_field2)

    # perturbation on one attractor (field2:E)
    if t == perturb_time:
        φ_E[t-1] += perturb_mag

    # update both fields
    φ_A[t] = φ_A[t-1] + field_dynamics(φ_A[t-1], φ_B[t-1], φ_C[t-1], damping_A, meta_term_1)
    φ_B[t] = φ_B[t-1] + field_dynamics(φ_B[t-1], φ_A[t-1], φ_C[t-1], damping_B, meta_term_1)
    φ_C[t] = φ_C[t-1] + field_dynamics(φ_C[t-1], φ_A[t-1], φ_B[t-1], damping_C, meta_term_1)

    φ_D[t] = φ_D[t-1] + field_dynamics(φ_D[t-1], φ_E[t-1], φ_F[t-1], damping_D, meta_term_2)
    φ_E[t] = φ_E[t-1] + field_dynamics(φ_E[t-1], φ_D[t-1], φ_F[t-1], damping_E, meta_term_2)
    φ_F[t] = φ_F[t-1] + field_dynamics(φ_F[t-1], φ_D[t-1], φ_E[t-1], damping_F, meta_term_2)

# ==========================================================
# --- Metrics ---
# ==========================================================

tail = slice(int(0.8 * N), None)

# intra-field coherence
Δ1 = np.mean([np.abs(φ_A - φ_B), np.abs(φ_B - φ_C), np.abs(φ_A - φ_C)], axis=0)
Δ2 = np.mean([np.abs(φ_D - φ_E), np.abs(φ_E - φ_F), np.abs(φ_D - φ_F)], axis=0)

# cross-field phase error
Δ_cross = np.abs(np.mean([φ_A, φ_B, φ_C], axis=0) - np.mean([φ_D, φ_E, φ_F], axis=0))

tail_mean_cross = np.mean(Δ_cross[tail])
cross_lock_ratio = np.mean(Δ_cross[tail] < lock_threshold)

corr_cross = np.corrcoef(np.mean([φ_A[tail], φ_B[tail], φ_C[tail]], axis=0),
                         np.mean([φ_D[tail], φ_E[tail], φ_F[tail]], axis=0))[0, 1]

# classification
if tail_mean_cross < 3e-3 and cross_lock_ratio > 0.9 and corr_cross > 0.97:
    classification = "✅ Stable meta-field coherence (predictive feedback lock)"
else:
    classification = "⚠️ Partial meta-field alignment (marginal stability)"

# ==========================================================
# --- Plots ---
# ==========================================================

plt.figure(figsize=(8, 4))
plt.plot(Δ1, label="|Δφ| Field1 (A,B,C)", alpha=0.7)
plt.plot(Δ2, label="|Δφ| Field2 (D,E,F)", alpha=0.7)
plt.plot(Δ_cross, label="|Δφ| Cross-field", color="k", linewidth=1.5)
plt.axvline(perturb_time, color="purple", linestyle=":", label="perturbation")
plt.axhline(lock_threshold, color="r", linestyle="--", label=f"lock threshold={lock_threshold}")
plt.title("P9c - Cross-Field Predictive Feedback (Meta-Field Coherence)")
plt.xlabel("time step")
plt.ylabel("|Δφ|")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P9c_MetaField_PhaseEvolution.png")

plt.figure(figsize=(6, 4))
plt.hist(Δ_cross[tail], bins=40, color="teal", edgecolor="k")
plt.axvline(lock_threshold, color="r", linestyle="--", label="lock threshold")
plt.title("P9c - Cross-Field Tail Error Distribution")
plt.xlabel("|Δφ_cross|")
plt.ylabel("Frequency")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P9c_MetaField_TailDistribution.png")

# ==========================================================
# --- Save JSON ---
# ==========================================================

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
    "K_meta": K_meta,
    "perturb_time": perturb_time,
    "perturb_mag": perturb_mag,
    "tail_mean_cross": float(tail_mean_cross),
    "cross_lock_ratio": float(cross_lock_ratio),
    "corr_cross": float(corr_cross),
    "classification": classification,
    "files": {
        "phase_plot": "PAEV_P9c_MetaField_PhaseEvolution.png",
        "tail_plot": "PAEV_P9c_MetaField_TailDistribution.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P9c_cross_field_feedback.json", "w") as f:
    json.dump(result, f, indent=2)

print("=== P9c - Cross-Field Predictive Feedback (Meta-Field Coherence) ===")
print(f"Tail ⟨|Δφ_cross|⟩={tail_mean_cross:.3e} | Lock Ratio={cross_lock_ratio:.2f} | Corr={corr_cross:.3f}")
print(f"-> {classification}")
print("✅ Results saved -> backend/modules/knowledge/P9c_cross_field_feedback.json")