import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import json
from datetime import datetime, timezone

# =====================================================
# P10p — Dynamic Trajectory Embedding on Fusion Surface
# =====================================================

np.random.seed(42)

# --- Load parameters from previous stages (P10m/o reference) ---
K_field = 0.1
K_global = 0.12
T = 1600
eta = 0.001

# Synthetic or previously saved phase trajectories
# (If you have φ(t) from P10m, replace these)
M = 3
phi = np.zeros((M, T))
phi[0, 0], phi[1, 0], phi[2, 0] = 0.0, 0.40, -0.25
omega = np.array([0.002, -0.001, 0.0005])

noise = 0.0025
alignment = dict(
    kappa_align_base=0.06,
    kappa_boost=0.18,
    curvature_gain=0.2,
    phase_damp=0.022,
    merge_bias_gain=0.009,
    bias_gain=0.004
)

def complex_order_parameter(phivec):
    z = np.exp(1j * phivec)
    zbar = z.mean()
    R = np.abs(zbar)
    psi = np.angle(zbar)
    return R, psi

# Simple dynamic evolution (nonlinear + alignment)
for t in range(1, T):
    R, psi = complex_order_parameter(phi[:, t-1])
    damp = 0.04 * (1 + 0.6 * (1 - R))
    for i in range(M):
        global_term = K_global * np.sin(psi - phi[i, t-1])
        align_term = -alignment["kappa_align_base"] * np.sin(phi[i, t-1] - np.mean(phi[:, t-1]))
        curvature = -alignment["curvature_gain"] * np.sin(2 * (phi[i, t-1] - np.mean(phi[:, t-1])))
        noise_term = np.random.normal(0, noise)
        phi[i, t] = phi[i, t-1] + eta * (omega[i] + global_term + align_term + curvature - damp * phi[i, t-1] + noise_term)

# Compute phase differences and R(t)
R_hist = np.zeros(T)
dphi1_hist, dphi2_hist = np.zeros(T), np.zeros(T)
for t in range(T):
    R, psi = complex_order_parameter(phi[:, t])
    R_hist[t] = R
    dphi1_hist[t] = phi[0, t] - phi[2, t]
    dphi2_hist[t] = phi[1, t] - phi[2, t]

# --- Construct surface (from P10o) ---
grid = np.linspace(-np.pi, np.pi, 80)
dphi1, dphi2 = np.meshgrid(grid, grid)
R_surface = np.cos(0.5 * (np.abs(dphi1) + np.abs(dphi2))) ** 2  # simplified approximation

# --- Plot trajectories on surface ---
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')

ax.plot_surface(dphi1, dphi2, R_surface, cmap='viridis', alpha=0.75, linewidth=0)
ax.plot(dphi1_hist, dphi2_hist, R_hist, color='red', linewidth=2.0, label="Phase Trajectory")
ax.scatter(dphi1_hist[-1], dphi2_hist[-1], R_hist[-1], color='black', s=50, label="Final Equilibrium")

ax.set_xlabel("Δφ₁ (rad)")
ax.set_ylabel("Δφ₂ (rad)")
ax.set_zlabel("R (coherence)")
ax.set_title("P10p — Dynamic Trajectory Embedding on Global Fusion Surface")
ax.legend()
plt.tight_layout()
plt.savefig("PAEV_P10p_DynamicTrajectoryEmbedding.png", dpi=240)
plt.close()

# --- Save summary ---
results = {
    "eta": eta,
    "noise": noise,
    "K_field": K_field,
    "K_global": K_global,
    "alignment": alignment,
    "metrics": {
        "R_final": float(R_hist[-1]),
        "mean_R": float(np.mean(R_hist[-200:])),
        "trajectory_span": [float(dphi1_hist[0]), float(dphi2_hist[0]), float(dphi1_hist[-1]), float(dphi2_hist[-1])],
    },
    "files": {"trajectory_plot": "PAEV_P10p_DynamicTrajectoryEmbedding.png"},
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P10p_dynamic_trajectory_embedding.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== P10p — Dynamic Trajectory Embedding ===")
print(f"Final R={results['metrics']['R_final']:.4f}, Mean R={results['metrics']['mean_R']:.4f}")
print("✅ Results saved → backend/modules/knowledge/P10p_dynamic_trajectory_embedding.json")