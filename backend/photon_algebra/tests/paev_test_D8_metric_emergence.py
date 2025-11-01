import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ============================================================
# Test D8 - Metric Emergence Test (Effective Spacetime Geometry)
# ============================================================

def compute_kappa_field(N=121, seed=8):
    """Generate a structured curvature field with small perturbations."""
    np.random.seed(seed)
    x = np.linspace(-1, 1, N)
    y = np.linspace(-1, 1, N)
    X, Y = np.meshgrid(x, y)

    # Base curvature: a localized wave packet with modulated symmetry
    kappa = np.exp(-5*(X**2 + Y**2)) * np.cos(6 * np.pi * X * Y)
    kappa += 0.05 * np.random.randn(N, N)
    return X, Y, kappa

def derive_metric_from_curvature(kappa):
    """Construct effective metric tensor from curvature gradients."""
    kx, ky = np.gradient(kappa)
    g_xx = 1.0 + kx**2
    g_yy = 1.0 + ky**2
    g_xy = kx * ky
    det_g = g_xx * g_yy - g_xy**2
    return g_xx, g_yy, g_xy, det_g

def compute_ricci_scalar(g_xx, g_yy, g_xy):
    """Estimate local Ricci-like scalar curvature."""
    gx_x, gx_y = np.gradient(g_xx)
    gy_x, gy_y = np.gradient(g_yy)
    gxy_x, gxy_y = np.gradient(g_xy)
    R = gx_y - gy_x + 0.5 * (gx_x - gy_y) - (gxy_x * gxy_y)
    return R

def normalize(x): return (x - np.min(x)) / (np.ptp(x) + 1e-12)

# === MAIN ===
print("=== Test D8 - Metric Emergence from Curvature Tensor ===")

X, Y, kappa = compute_kappa_field()
g_xx, g_yy, g_xy, det_g = derive_metric_from_curvature(kappa)
R = compute_ricci_scalar(g_xx, g_yy, g_xy)

# Metric consistency
mean_det = np.mean(det_g)
std_det = np.std(det_g)
print(f"Metric determinant mean={mean_det:.4e}, std={std_det:.4e}")

# === Visualization ===
plt.figure(figsize=(6,6))
plt.imshow(kappa, cmap="inferno", extent=[-1,1,-1,1])
plt.title("Test D8 - Base Curvature Field κ(x,y)")
plt.colorbar(label="κ curvature")
plt.tight_layout()
plt.savefig("PAEV_TestD8_CurvatureField.png")
plt.close()

plt.figure(figsize=(6,6))
plt.imshow(det_g, cmap="viridis", extent=[-1,1,-1,1])
plt.title("Test D8 - Metric Determinant det(g)")
plt.colorbar(label="det(g)")
plt.tight_layout()
plt.savefig("PAEV_TestD8_MetricDeterminant.png")
plt.close()

plt.figure(figsize=(6,6))
plt.imshow(R, cmap="coolwarm", extent=[-1,1,-1,1])
plt.title("Test D8 - Ricci-like Scalar Curvature R(x,y)")
plt.colorbar(label="R (arb. units)")
plt.tight_layout()
plt.savefig("PAEV_TestD8_RicciScalar.png")
plt.close()

# Save animated Ricci evolution (perturbed metric flow)
frames = []
for s in np.linspace(0, 2*np.pi, 40):
    k_mod = kappa * np.cos(s)
    _, _, _, det_mod = derive_metric_from_curvature(k_mod)
    R_mod = compute_ricci_scalar(g_xx, g_yy, g_xy)
    frame = (normalize(R_mod) * 255).astype(np.uint8)
    frames.append(np.stack([frame]*3, axis=-1))
imageio.mimsave("PAEV_TestD8_MetricEvolution.gif", frames, fps=10)

print("✅ Saved curvature, determinant, and Ricci plots.")
print("✅ Saved metric evolution animation (Ricci modulation).")

print("\n=== Test D8 complete ===")
print(f"Average determinant ⟨det(g)⟩ = {mean_det:.4f}")
print(f"Curvature variability σ = {std_det:.4f}")