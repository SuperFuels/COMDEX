import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# ==========================================================
# P9d - Self-Adaptive Meta-Learning Coupling
# ==========================================================

np.random.seed(42)

# --- Base physical parameters ---
η = 0.001
damping = 0.042
leak = 0.0085
noise_base = 0.0028
K_field = 0.08

# --- Meta-control base parameters ---
K_meta_init = 0.02
servo_p_init = 0.12
servo_i_init = 0.0012
servo_i_max = 0.03
servo_d = 0.02
learning_rate = 0.25  # meta-learning rate

# --- Simulation config ---
N = 1200
EPOCHS = 8
lock_threshold = 0.009
perturb_time = 800
perturb_mag = 0.002

# ----------------------------------------------------------
# Meta-learning state
best_lock = 0
best_params = {}
history = []

# ==========================================================
# --- Helper function for one field pair run ---
def run_field_pair(K_meta_base, servo_p, servo_i):
    phi_A = np.zeros(N)
    phi_B = np.zeros(N)
    drift = np.zeros(N)
    err_cross = np.zeros(N)

    for t in range(1, N):
        noise_A = np.random.normal(0, noise_base)
        noise_B = np.random.normal(0, noise_base)
        drift[t] = 0.0012 * np.tanh(t / 900)
        if t == perturb_time:
            phi_A[t-1] += perturb_mag

        dA = -damping * phi_A[t-1] + K_field * (phi_B[t-1] - phi_A[t-1]) + noise_A
        dB = -damping * phi_B[t-1] + K_field * (phi_A[t-1] - phi_B[t-1]) + noise_B
        phi_A[t] = phi_A[t-1] + dA
        phi_B[t] = phi_B[t-1] + dB

        # Cross-field coupling (adaptive)
        cross_err = abs(phi_A[t] - phi_B[t])
        err_cross[t] = cross_err

        # Meta feedback adjustment (like Hebbian reinforcement)
        adj = servo_p * (lock_threshold - cross_err)
        servo_i = np.clip(servo_i + adj * 0.1, 0, servo_i_max)
        K_meta_base = min(K_meta_base + servo_i * 0.2, 0.55)

    tail = slice(int(0.8 * N), None)
    tail_mean = np.mean(err_cross[tail])
    tail_lock_ratio = np.mean(err_cross[tail] < lock_threshold)
    slope = np.polyfit(np.arange(len(err_cross[tail])), err_cross[tail], 1)[0]

    return {
        "err_cross": err_cross,
        "tail_mean": float(tail_mean),
        "tail_lock_ratio": float(tail_lock_ratio),
        "slope": float(slope),
        "final_K_meta": float(K_meta_base),
        "final_servo_i": float(servo_i)
    }

# ==========================================================
# --- Meta-learning loop ---
for epoch in range(EPOCHS):
    result = run_field_pair(K_meta_init, servo_p_init, servo_i_init)
    tail_lock = result["tail_lock_ratio"]

    # Reinforce parameters if lock improves
    if tail_lock > best_lock:
        best_lock = tail_lock
        best_params = {
            "K_meta": result["final_K_meta"],
            "servo_i": result["final_servo_i"],
            "epoch": epoch
        }

    # Hebbian-style parameter reinforcement
    dK_meta = learning_rate * (tail_lock - best_lock)
    dservo_p = learning_rate * (tail_lock - best_lock) * 0.5
    K_meta_init = np.clip(K_meta_init + dK_meta, 0.01, 0.6)
    servo_p_init = np.clip(servo_p_init + dservo_p, 0.05, 0.25)

    history.append({
        "epoch": epoch,
        "tail_lock": tail_lock,
        "tail_mean": result["tail_mean"],
        "K_meta": result["final_K_meta"],
        "servo_p": servo_p_init
    })

# ==========================================================
# --- Visualization ---
epochs = [h["epoch"] for h in history]
lock_scores = [h["tail_lock"] for h in history]
K_values = [h["K_meta"] for h in history]
servo_ps = [h["servo_p"] for h in history]

plt.figure(figsize=(7, 4))
plt.plot(epochs, lock_scores, marker="o")
plt.title("P9d - Meta-Learning Lock Ratio Progression")
plt.xlabel("Epoch")
plt.ylabel("Lock Ratio")
plt.tight_layout()
plt.savefig("PAEV_P9d_MetaLearning_LockProgress.png")

plt.figure(figsize=(7, 4))
plt.plot(epochs, K_values, label="K_meta")
plt.plot(epochs, servo_ps, label="servo_p")
plt.title("P9d - Adaptive Gains Across Epochs")
plt.xlabel("Epoch")
plt.ylabel("Gain Value")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P9d_MetaLearning_Gains.png")

# ==========================================================
# --- Save results ---
result_json = {
    "eta": η,
    "damping": damping,
    "leak": leak,
    "noise_base": noise_base,
    "K_field": K_field,
    "epochs": EPOCHS,
    "learning_rate": learning_rate,
    "best_lock_ratio": best_lock,
    "best_params": best_params,
    "history": history,
    "classification": (
        "✅ Stable meta-field learning convergence"
        if best_lock > 0.7
        else "⚠️ Partial convergence (marginal)"
    ),
    "files": {
        "lock_plot": "PAEV_P9d_MetaLearning_LockProgress.png",
        "gain_plot": "PAEV_P9d_MetaLearning_Gains.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P9d_meta_learning.json", "w") as f:
    json.dump(result_json, f, indent=2)

print("=== P9d - Self-Adaptive Meta-Learning Coupling ===")
print(f"Best lock ratio = {best_lock:.3f} @ epoch {best_params.get('epoch', '-')}")
print(f"Final K_meta = {best_params.get('K_meta', 'N/A'):.3f} | servo_i = {best_params.get('servo_i', 'N/A'):.4f}")
print(f"-> {result_json['classification']}")
print("✅ Results saved -> backend/modules/knowledge/P9d_meta_learning.json")