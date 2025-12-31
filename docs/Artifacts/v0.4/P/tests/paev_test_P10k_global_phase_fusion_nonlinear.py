import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# ==========================================================
# P10k - Global Phase Fusion via Nonlinear Merge Torque
# ==========================================================

np.random.seed(17)

T = 1600
M = 3
eta = 0.001
damping_base = 0.04
leak = 0.0085
noise = 0.0023

K_field = 0.06          # slightly reduced for phase fluidity
K_global_min = 0.05
K_global_max = 0.3
K_global = 0.12
R_target = 0.992

# PID controller
kp, ki, kd = 0.9, 0.03, 0.04
i_min, i_max = -0.15, 0.15
d_lpf, dead_zone = 0.15, 4e-4

# Alignment and nonlinear merge parameters
kappa_align_base = 0.06
kappa_boost = 0.18
curvature_gain = 0.20
phase_damp = 0.022
merge_bias_gain = 0.009   # stronger
shared_noise_scale = 2.5e-4

PERT_TIME = 800
PERT_MAG = 0.015

phi = np.zeros((M, T))
phi[0, 0], phi[1, 0], phi[2, 0] = 0.0, 0.4, -0.25
omega = np.array([0.002, -0.001, 0.0005])

e_prev = e_int = e_deriv = 0.0
R_hist = np.zeros(T)
Kglob_hist = np.zeros(T)
align_gain_hist = np.zeros(T)

def complex_order_parameter(phivec):
    z = np.exp(1j * phivec)
    zbar = z.mean()
    return np.abs(zbar), np.angle(zbar)

for t in range(1, T):
    R, psi = complex_order_parameter(phi[:, t-1])
    R_hist[t-1] = R

    # PID control
    e = R_target - R
    if abs(e) > dead_zone:
        e_int = np.clip(e_int + e, i_min, i_max)
    e_deriv = (1 - d_lpf) * e_deriv + d_lpf * (e - e_prev)
    e_prev = e
    K_global = np.clip(K_global + kp * e + ki * e_int + kd * e_deriv,
                       K_global_min, K_global_max)
    Kglob_hist[t-1] = K_global

    damp = damping_base * (1.0 + 0.5 * (1.0 - R))
    kappa_align = kappa_align_base if t < PERT_TIME else kappa_boost
    if R > 0.996:
        kappa_align *= 0.985  # adaptive decay post-lock
    align_gain_hist[t-1] = kappa_align

    shared_noise = np.random.normal(0, shared_noise_scale)
    phi_mean = np.mean(phi[:, t-1])

    for i in range(M):
        local = np.sum(np.sin(phi[:, t-1] - phi[i, t-1])) - np.sin(0)
        local *= K_field / (M - 1)
        global_term = K_global * np.sin(psi - phi[i, t-1])
        align_term = -kappa_align * np.sin(phi[i, t-1] - phi_mean)
        curvature_term = -curvature_gain * np.sin(2 * (phi[i, t-1] - phi_mean))
        phase_error = phi[i, t-1] - phi_mean
        damp_term = -phase_damp * phase_error

        # nonlinear merge bias (phase fusion)
        merge_bias = -merge_bias_gain * np.sin(3 * (phi[i, t-1] - psi)) * np.exp(-abs(phi[i, t-1] - psi))

        adaptive_drag = -0.006 * np.sign(phase_error) * (abs(phase_error) ** 1.5)

        xi = np.random.normal(0, noise)
        xi += 0.00015 * np.sin(phi_mean - phi[i, t-1])  # convergence noise

        dphi = (omega[i] + local + global_term +
                align_term + curvature_term + damp_term +
                merge_bias + adaptive_drag
                - damp * phi[i, t-1] - leak * phi[i, t-1]
                + xi + shared_noise)
        phi[i, t] = phi[i, t-1] + eta * dphi

    if t == PERT_TIME:
        phi[1, t:] += PERT_MAG

# === Metrics ===
R, psi = complex_order_parameter(phi[:, -1])
R_hist[-1] = R
Kglob_hist[-1] = K_global

tail = slice(int(0.8 * T), None)
R_tail = R_hist[tail]
R_tail_mean = float(np.mean(R_tail))
R_tail_slope = float(np.polyfit(np.arange(len(R_tail)), R_tail, 1)[0])
lock_ratio_R = float(np.mean(R_tail > R_target))

phi_mean_series = np.mean(phi, axis=0)
abs_errs = np.abs(phi - phi_mean_series)
tail_err = abs_errs[:, tail].mean(axis=0)
lock_ratio_phi = float(np.mean(tail_err < 0.004))
tail_mean_error = float(np.mean(tail_err))

relock = None
for t in range(PERT_TIME + 5, T - 100):
    seg = R_hist[t:t + 100]
    if np.mean(seg > R_target) >= 0.95:
        relock = int(t - PERT_TIME)
        break

if lock_ratio_R >= 0.98 and lock_ratio_phi >= 0.5:
    verdict = "✅ Full Global Phase Lock"
elif lock_ratio_R >= 0.8:
    verdict = "⚠️ Partial Global Coherence"
else:
    verdict = "❌ No Global Lock"

# === Plots ===
plt.figure(figsize=(10, 4.8))
for i in range(M):
    plt.plot(phi[i], label=f"Field {i+1}", linewidth=1.2)
plt.plot(np.unwrap(np.angle(np.exp(1j * phi).mean(axis=0))),
         "k--", label="Global Mean")
plt.axvline(PERT_TIME, color="purple", linestyle="--", label="Perturbation")
plt.title("P10k - Global Phase Fusion (Nonlinear Merge Torque)")
plt.xlabel("time step"); plt.ylabel("phase")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_P10k_GlobalField_PhaseEvolution.png")

plt.figure(figsize=(8.8, 4.6))
plt.plot(R_hist, label="R(t)")
plt.axhline(R_target, color="red", linestyle="--", alpha=0.6, label=f"R_target={R_target}")
plt.plot((Kglob_hist - K_global_min) / (K_global_max - K_global_min),
         "gray", linestyle="--", alpha=0.7, label="scaled K_global(t)")
plt.plot(align_gain_hist / np.max(align_gain_hist),
         "orange", linestyle=":", alpha=0.8, label="scaled κ_align")
plt.axvline(PERT_TIME, color="purple", linestyle="--", label="Perturbation")
plt.title("P10k - Order Parameter R(t) & Nonlinear Fusion Control")
plt.xlabel("time step"); plt.ylabel("Normalized Value")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_P10k_GlobalField_OrderParameter.png")

# === Save ===
results = {
    "eta": eta,
    "noise": noise,
    "damping_base": damping_base,
    "leak": leak,
    "K_field": K_field,
    "alignment": {
        "kappa_align_base": kappa_align_base,
        "kappa_boost": kappa_boost,
        "curvature_gain": curvature_gain,
        "phase_damp": phase_damp,
        "merge_bias_gain": merge_bias_gain
    },
    "metrics": {
        "R_tail_mean": R_tail_mean,
        "R_tail_slope": R_tail_slope,
        "lock_ratio_R": lock_ratio_R,
        "lock_ratio_phi": lock_ratio_phi,
        "tail_mean_phase_error": tail_mean_error,
        "relock_time": relock
    },
    "classification": verdict,
    "files": {
        "phase_plot": "PAEV_P10k_GlobalField_PhaseEvolution.png",
        "order_plot": "PAEV_P10k_GlobalField_OrderParameter.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P10k_global_phase_fusion_nonlinear.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== P10k - Global Phase Fusion (Nonlinear) ===")
print(f"R_tail_mean={R_tail_mean:.3f} | lock_R={lock_ratio_R:.2f} | "
      f"lock_phi={lock_ratio_phi:.2f} | slope={R_tail_slope:.2e} | re-lock={relock}")
print(f"-> {verdict}")
print("✅ Results saved -> backend/modules/knowledge/P10k_global_phase_fusion_nonlinear.json")