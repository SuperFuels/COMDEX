import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime, timezone

# =====================================================
# P10n — Global Fusion Energy Landscape Visualization
# =====================================================

np.random.seed(77)

# --- Parameters (from P10m certified configuration) ---
M = 3
eta = 0.001
noise = 0.0025
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

# --- Derived helper functions ---
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

# --- 1. Energy landscape scan (Δφ1, Δφ2 grid) ---
grid = np.linspace(-np.pi, np.pi, 120)
dphi1, dphi2 = np.meshgrid(grid, grid)
energy = np.zeros_like(dphi1)
grad_norm = np.zeros_like(dphi1)
Rvals = np.zeros_like(dphi1)

# base center (φ₃ = 0)
for i in range(len(grid)):
    for j in range(len(grid)):
        phi = np.array([dphi1[i,j], dphi2[i,j], 0.0])
        dphi_vec, R, _ = phase_dynamics(phi)
        energy[i,j] = -R  # “potential-like”: high R = low energy
        grad_norm[i,j] = np.linalg.norm(dphi_vec)
        Rvals[i,j] = R

# --- 2. Normalize ---
energy -= energy.min()
energy /= energy.max()

# --- 3. Vector field for phase convergence ---
skip = 6
sample_idx = np.arange(0, len(grid), skip)
U = np.zeros((len(sample_idx), len(sample_idx)))
V = np.zeros_like(U)

for i, a in enumerate(sample_idx):
    for j, b in enumerate(sample_idx):
        phi = np.array([grid[a], grid[b], 0.0])
        dphi_vec, _, _ = phase_dynamics(phi)
        U[i, j] = dphi_vec[0]
        V[i, j] = dphi_vec[1]

# --- 4. Plot (3 panels) ---
fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))

# (a) Energy landscape (R → potential)
im0 = axes[0].imshow(energy, extent=[-np.pi, np.pi, -np.pi, np.pi],
                     origin="lower", cmap="magma", aspect="auto")
axes[0].set_title("P10n — Global Fusion Energy Landscape")
axes[0].set_xlabel("Δφ₁ (rad)")
axes[0].set_ylabel("Δφ₂ (rad)")
plt.colorbar(im0, ax=axes[0], label="Normalized Energy (−R)")

# (b) Convergence vector field (phase flow)
axes[1].imshow(Rvals, extent=[-np.pi, np.pi, -np.pi, np.pi],
               origin="lower", cmap="viridis", aspect="auto", alpha=0.9)
axes[1].quiver(grid[sample_idx], grid[sample_idx], U, V, color="white", scale=40)
axes[1].set_title("Phase Flow Field (Convergence toward ψ)")
axes[1].set_xlabel("Δφ₁")
axes[1].set_ylabel("Δφ₂")

# (c) Gradient magnitude (stability contour)
im2 = axes[2].imshow(grad_norm, extent=[-np.pi, np.pi, -np.pi, np.pi],
                     origin="lower", cmap="plasma", aspect="auto")
axes[2].set_title("Effective Stability (‖∂φ̇‖ norm)")
axes[2].set_xlabel("Δφ₁")
axes[2].set_ylabel("Δφ₂")
plt.colorbar(im2, ax=axes[2], label="‖gradient‖")

plt.tight_layout()
plt.savefig("PAEV_P10n_GlobalFusionLandscape.png", dpi=200)

# --- 5. Compute global minima / equilibrium stats ---
min_idx = np.unravel_index(np.argmin(energy), energy.shape)
phi_min = (grid[min_idx[1]], grid[min_idx[0]])
R_min = Rvals[min_idx]
grad_min = grad_norm[min_idx]

results = {
    "alignment": alignment,
    "parameters": {"noise": noise, "K_field": K_field, "K_global": K_global},
    "grid_size": len(grid),
    "equilibrium": {
        "min_energy_location": {"Δφ1": phi_min[0], "Δφ2": phi_min[1]},
        "R_at_min": float(R_min),
        "gradient_norm_at_min": float(grad_min)
    },
    "files": {"landscape": "PAEV_P10n_GlobalFusionLandscape.png"},
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P10n_global_fusion_landscape.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== P10n — Global Fusion Energy Landscape ===")
print(f"Equilibrium min: Δφ1={phi_min[0]:.3f}, Δφ2={phi_min[1]:.3f}, R={R_min:.3f}, grad_norm={grad_min:.3e}")
print("✅ Results saved → backend/modules/knowledge/P10n_global_fusion_landscape.json")