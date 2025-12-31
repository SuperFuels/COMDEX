import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import json
from datetime import datetime, timezone

# =====================================================
# P10o - 3D Global Fusion Surface (R Landscape)
# =====================================================

np.random.seed(77)

# --- Parameters (from P10n certified model) ---
M = 3
K_field = 0.1
K_global = 0.12

alignment = dict(
    kappa_align_base=0.06,
    kappa_boost=0.18,
    curvature_gain=0.20,
    phase_damp=0.022,
    merge_bias_gain=0.009,
    bias_gain=0.004
)

# --- Functions ---
def complex_order_parameter(phi):
    z = np.exp(1j * phi)
    zbar = z.mean()
    return np.abs(zbar), np.angle(zbar)

def local_field(phi, Kf=K_field):
    M = len(phi)
    out = np.zeros(M)
    for i in range(M):
        for j in range(M):
            if j != i:
                out[i] += np.sin(phi[j] - phi[i])
    return Kf * out / (M - 1)

def phase_dynamics(phi):
    R, psi = complex_order_parameter(phi)
    field_term = local_field(phi)
    phi_mean = np.mean(phi)
    dphi = np.zeros_like(phi)
    for i in range(M):
        global_term = K_global * np.sin(psi - phi[i])
        align_term = -alignment["kappa_align_base"] * np.sin(phi[i] - phi_mean)
        curvature_term = -alignment["curvature_gain"] * np.sin(2 * (phi[i] - phi_mean))
        damp_term = -alignment["phase_damp"] * (phi[i] - phi_mean)
        merge_bias = -alignment["merge_bias_gain"] * np.sin(3 * (phi[i] - psi))
        bias_term = -alignment["bias_gain"] * np.sign(phi[i] - psi)
        dphi[i] = field_term[i] + global_term + align_term + curvature_term + damp_term + merge_bias + bias_term
    return dphi, R, psi

# --- Phase grid ---
grid = np.linspace(-np.pi, np.pi, 100)
dphi1, dphi2 = np.meshgrid(grid, grid)
Rvals = np.zeros_like(dphi1)

for i in range(len(grid)):
    for j in range(len(grid)):
        phi = np.array([dphi1[i, j], dphi2[i, j], 0.0])
        _, R, _ = phase_dynamics(phi)
        Rvals[i, j] = R

# --- Equilibrium detection ---
min_idx = np.unravel_index(np.argmax(Rvals), Rvals.shape)
phi_eq = (grid[min_idx[1]], grid[min_idx[0]])
R_eq = Rvals[min_idx]

# --- Plot: 3D Surface ---
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')

surf = ax.plot_surface(dphi1, dphi2, Rvals, cmap='viridis', linewidth=0, antialiased=True, alpha=0.95)
ax.set_xlabel("Δφ1 (rad)")
ax.set_ylabel("Δφ2 (rad)")
ax.set_zlabel("R (coherence)")
ax.set_title("P10o - 3D Global Fusion Surface (R vs Phase Dispersion)")

# Add contours + equilibrium marker
ax.contour(dphi1, dphi2, Rvals, zdir='z', offset=Rvals.min(), cmap='viridis', alpha=0.6)
ax.scatter(phi_eq[0], phi_eq[1], R_eq, color='red', s=60, label="Equilibrium (max R)")
ax.legend()

plt.tight_layout()
plt.savefig("PAEV_P10o_GlobalFusionSurface.png", dpi=240)
plt.close()

# --- Save data ---
results = {
    "alignment": alignment,
    "parameters": {"K_field": K_field, "K_global": K_global},
    "grid_size": len(grid),
    "equilibrium": {
        "Δφ1_eq": float(phi_eq[0]),
        "Δφ2_eq": float(phi_eq[1]),
        "R_eq": float(R_eq)
    },
    "files": {"surface": "PAEV_P10o_GlobalFusionSurface.png"},
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P10o_global_fusion_surface.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== P10o - 3D Global Fusion Surface ===")
print(f"Equilibrium: Δφ1={phi_eq[0]:.3f}, Δφ2={phi_eq[1]:.3f}, R_eq={R_eq:.4f}")
print("✅ Results saved -> backend/modules/knowledge/P10o_global_fusion_surface.json")