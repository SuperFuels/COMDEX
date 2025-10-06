import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# ==========================================================
# P9b — Predictive Field Resilience (Perturbation & Drift)
# ==========================================================

np.random.seed(42)
N = 1200  # extended steps for drift observation

# --- base parameters (from P9) ---
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
K_field = 0.08
lock_threshold = 0.009

# --- perturbation + drift parameters ---
perturb_time = 600
perturb_mag = 0.002
drift_amp = 0.0012
tau_drift = 1200.0

# --- initialize 3 attractors ---
ϕ_A = np.zeros(N)
ϕ_B = np.zeros(N)
ϕ_C = np.zeros(N)

ϕ_A[0], ϕ_B[0], ϕ_C[0] = 0.0, 0.05, -0.03

damping_A, damping_B, damping_C = damping, damping * 1.03, damping * 0.97

# --- simulation loop ---
for t in range(1, N):
    noise_A = np.random.normal(0, noise_scale)
    noise_B = np.random.normal(0, noise_scale)
    noise_C = np.random.normal(0, noise_scale)

    # introduce perturbation at t=perturb_time
    if t == perturb_time:
        ϕ_B[t-1] += perturb_mag

    # apply slow drift bias
    drift_term = drift_amp * (1 - np.exp(-t / tau_drift))

    dϕ_A = -damping_A * ϕ_A[t-1] + K_field * (ϕ_B[t-1] + ϕ_C[t-1] - 2 * ϕ_A[t-1]) + noise_A + drift_term
    dϕ_B = -damping_B * ϕ_B[t-1] + K_field * (ϕ_A[t-1] + ϕ_C[t-1] - 2 * ϕ_B[t-1]) + noise_B + drift_term
    dϕ_C = -damping_C * ϕ_C[t-1] + K_field * (ϕ_A[t-1] + ϕ_B[t-1] - 2 * ϕ_C[t-1]) + noise_C + drift_term

    ϕ_A[t] = ϕ_A[t-1] + dϕ_A
    ϕ_B[t] = ϕ_B[t-1] + dϕ_B
    ϕ_C[t] = ϕ_C[t-1] + dϕ_C

# --- metrics ---
Δ_AB = np.abs(ϕ_A - ϕ_B)
Δ_BC = np.abs(ϕ_B - ϕ_C)
Δ_AC = np.abs(ϕ_A - ϕ_C)

mov_w = 31
Δ_field = np.mean([Δ_AB, Δ_BC, Δ_AC], axis=0)
mov_mean = np.convolve(Δ_field, np.ones(mov_w) / mov_w, mode='same')

tail = slice(int(0.8 * N), None)
tail_mean = np.mean(Δ_field[tail])
tail_lock_ratio = np.mean(Δ_field[tail] < lock_threshold)

# --- re-lock time after perturbation ---
post = Δ_field[perturb_time:]
relock_idx = np.argmax(np.convolve((post < lock_threshold).astype(int), np.ones(100), mode='valid') > 95)
relock_time = int(relock_idx) if relock_idx > 0 else None

# --- drift breakpoint ---
drift_break_idx = np.argmax(Δ_field[tail] > lock_threshold * 2)
drift_breakpoint = int(tail.start + drift_break_idx) if drift_break_idx > 0 else None

# --- classification ---
if tail_lock_ratio > 0.9 and tail_mean < 3e-3:
    classification = "✅ Stable predictive field (resilient & coherent)"
else:
    classification = "⚠️ Partial resilience (marginal stability)"

# ==========================================================
# --- Plot 1: Phase Error Evolution ---
plt.figure(figsize=(8, 4))
plt.plot(Δ_field, label="|Δφ_field| avg", color="tab:blue")
plt.axvline(perturb_time, color="purple", linestyle=":", label="perturbation")
plt.axhline(lock_threshold, color="r", linestyle="--", label=f"lock threshold={lock_threshold}")
if drift_breakpoint:
    plt.axvline(drift_breakpoint, color="gray", linestyle="--", label="drift breakpoint")
plt.title("P9b — Field Phase Error Evolution (Perturbed + Drifted)")
plt.xlabel("time step")
plt.ylabel("|Δφ|")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P9b_Field_PhaseEvolution.png")

# --- Plot 2: Tail Stability ---
plt.figure(figsize=(6, 4))
plt.hist(Δ_field[tail], bins=40, color="skyblue", edgecolor="k")
plt.axvline(lock_threshold, color="r", linestyle="--", label="lock threshold")
plt.title("P9b — Tail Phase Error Distribution")
plt.xlabel("|Δφ_field|")
plt.ylabel("Frequency")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P9b_Field_TailDistribution.png")

# ==========================================================
# --- Save JSON ---
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
    "perturb_time": perturb_time,
    "perturb_mag": perturb_mag,
    "drift_amp": drift_amp,
    "tau_drift": tau_drift,
    "tail_mean_field_error": float(tail_mean),
    "tail_lock_ratio": float(tail_lock_ratio),
    "relock_time": relock_time,
    "drift_breakpoint": drift_breakpoint,
    "classification": classification,
    "files": {
        "phase_plot": "PAEV_P9b_Field_PhaseEvolution.png",
        "tail_plot": "PAEV_P9b_Field_TailDistribution.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P9b_field_resilience.json", "w") as f:
    json.dump(result, f, indent=2)

print("=== P9b — Predictive Field Resilience (Perturbation + Drift) ===")
print(f"Tail ⟨|Δφ_field|⟩={tail_mean:.3e} | Lock Ratio={tail_lock_ratio:.2f}")
print(f"Re-lock time={relock_time} | Drift break={drift_breakpoint}")
print(f"→ {classification}")
print("✅ Results saved → backend/modules/knowledge/P9b_field_resilience.json")