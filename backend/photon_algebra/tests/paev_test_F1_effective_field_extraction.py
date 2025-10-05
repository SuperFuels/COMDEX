# ==========================================================
# Test F1 — Effective Field Extraction
#   Fit an effective PDE and Lagrangian from simulated data
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# numerics & helpers
# ----------------------------
def laplacian(Z):
    return (
        -4.0 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

def grad_xy(Z):
    gx = 0.5 * (np.roll(Z, -1, 1) - np.roll(Z, 1, 1))
    gy = 0.5 * (np.roll(Z, -1, 0) - np.roll(Z, 1, 0))
    return gx, gy

def div_xy(Ax, Ay):
    dx = 0.5 * (np.roll(Ax, -1, 1) - np.roll(Ax, 1, 1))
    dy = 0.5 * (np.roll(Ay, -1, 0) - np.roll(Ay, 1, 0))
    return dx + dy

def mse(a, b): return float(np.mean((a - b) ** 2))

# ----------------------------
# simulation parameters
# ----------------------------
N = 64
steps = 140
dt = 0.02

# gentle, stable couplings (kept small to avoid D10 blow-ups)
c = 0.9          # wave speed for theta
gamma = 0.02     # theta damping
eta = 0.08       # curvature relaxation
chi = 0.20       # curvature↔phase coupling
zeta = 0.04      # curvature self-diffusion
noise_amp = 5e-4 # small stochastic drive

x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# initial fields
rng = np.random.default_rng(42)
theta = 0.2 * np.exp(-(X**2 + Y**2) / 0.5) + 0.05 * rng.standard_normal((N, N))
theta_t = 0.0 * theta
kappa = 0.05 * np.exp(-(X**2 + Y**2) / 0.4) + 0.02 * rng.standard_normal((N, N))

# storage for system ID
# we’ll collect (inputs, targets) after a warmup
collect_from = 20
theta_tt_list = []
theta_feat_list = []
kappa_t_list = []
kappa_feat_list = []

# frames for quick visual sanity
frames = []

# ----------------------------
# evolve & collect
# ----------------------------
for t in range(steps):
    # wave-like theta with curvature feedback
    lap_th = laplacian(theta)
    gx, gy = grad_xy(theta)
    # conservative coupling: div( kappa * grad theta )
    Jx, Jy = kappa * gx, kappa * gy
    div_J = div_xy(Jx, Jy)
    # theta acceleration
    theta_tt = (c**2) * lap_th - gamma * theta_t + chi * div_J

    # update theta
    theta_t = theta_t + dt * theta_tt
    theta   = theta   + dt * theta_t

    # curvature relaxes + driven by phase gradients
    grad2 = gx**2 + gy**2
    kappa_t = zeta * laplacian(kappa) - eta * kappa + chi * (grad2 - np.mean(grad2))
    # small noise (zero-mean)
    kappa_t += noise_amp * rng.standard_normal((N, N))
    kappa = kappa + dt * kappa_t

    # collect supervised pairs after warmup
    if t >= collect_from:
        # θ̈ target and features: [∇²θ, κ θ, ∇·(κ∇θ)]
        feats_theta = np.stack([lap_th, kappa * theta, div_J], axis=-1)
        theta_feat_list.append(feats_theta.reshape(-1, 3))
        theta_tt_list.append(theta_tt.reshape(-1))

        # κ̇ target and features: [∇²κ, (∇θ)², κ]
        feats_kappa = np.stack([laplacian(kappa), grad2, kappa], axis=-1)
        kappa_feat_list.append(feats_kappa.reshape(-1, 3))
        kappa_t_list.append(kappa_t.reshape(-1))

    # make a frame every ~15 steps
    if t % 15 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7.5, 3.3))
        im0 = ax[0].imshow(theta, cmap="twilight", vmin=-np.pi, vmax=np.pi)
        ax[0].set_title(f"θ phase @ step {t}")
        ax[0].axis("off")
        im1 = ax[1].imshow(kappa, cmap="magma")
        ax[1].set_title("κ curvature")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# assemble regression matrices
# ----------------------------
Theta_X = np.concatenate(theta_feat_list, axis=0)         # (M, 3)
Theta_y = np.concatenate(theta_tt_list, axis=0)           # (M,)
Kappa_X = np.concatenate(kappa_feat_list, axis=0)         # (M, 3)
Kappa_y = np.concatenate(kappa_t_list, axis=0)            # (M,)

# least squares + basic uncertainty (diag from (X^T X)⁻¹ σ²)
def fit_with_uncertainty(X, y):
    w, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
    # estimated noise variance
    dof = max(len(y) - X.shape[1], 1)
    sigma2 = float(residuals / dof) if residuals.size else float(np.mean((y - X @ w)**2))
    cov = sigma2 * np.linalg.pinv(X.T @ X)
    errs = np.sqrt(np.maximum(np.diag(cov), 0.0))
    return w, errs, sigma2

(c1, c2, c3), (ec1, ec2, ec3), sig_t = fit_with_uncertainty(Theta_X, Theta_y)
(d1, d2, d3), (ed1, ed2, ed3), sig_k = fit_with_uncertainty(Kappa_X, Kappa_y)

# ----------------------------
# map to an effective Lagrangian (heuristic)
# θ̈ ≈ c1 ∇²θ + c2 κθ + c3 ∇·(κ∇θ)
# κ̇ ≈ d1 ∇²κ + d2 (∇θ)² + d3 κ
# A minimal quadratic ℒ consistent with these flows:
# ℒ ≈ a (∂tθ)² − b (∇θ)² − e κ(∇θ)² − f κ² − g (∇κ)²
# identify: b ~ - c1/2, e ~ - c3/2, f ~ - d3/2, g ~ - d1/2
# a is set to +1/2 by convention (units choice).
# ----------------------------
a = 0.5
b = -0.5 * c1
e = -0.5 * c3
f = -0.5 * d3
g = -0.5 * d1

# ----------------------------
# diagnostics plots
# ----------------------------
# residual histograms
plt.figure(figsize=(6,4))
plt.hist(Theta_y - Theta_X @ np.array([c1,c2,c3]), bins=80, alpha=0.8)
plt.title("F1 — Residuals (θ̈ fit)")
plt.tight_layout()
plt.savefig("PAEV_TestF1_EffectiveField_Residuals_theta.png")
plt.close()
print("✅ Saved file: PAEV_TestF1_EffectiveField_Residuals_theta.png")

plt.figure(figsize=(6,4))
plt.hist(Kappa_y - Kappa_X @ np.array([d1,d2,d3]), bins=80, alpha=0.8, color="orange")
plt.title("F1 — Residuals (κ̇ fit)")
plt.tight_layout()
plt.savefig("PAEV_TestF1_EffectiveField_Residuals_kappa.png")
plt.close()
print("✅ Saved file: PAEV_TestF1_EffectiveField_Residuals_kappa.png")

# predicted vs actual scatter (downsample for speed/size)
def scatter_pred_actual(X, y, w, title, fname):
    idx = np.linspace(0, len(y)-1, 20000, dtype=int)
    y_hat = X[idx] @ w
    plt.figure(figsize=(5.5,5))
    plt.scatter(y[idx], y_hat, s=2, alpha=0.3)
    # best fit line
    A = np.vstack([y[idx], np.ones_like(y_hat)]).T
    m, b0 = np.linalg.lstsq(A, y_hat, rcond=None)[0]
    xs = np.linspace(float(np.min(y[idx])), float(np.max(y[idx])), 200)
    plt.plot(xs, m*xs + b0, 'r-', lw=2, label=f"fit: y≈{m:.2f}x+{b0:.2e}")
    plt.xlabel("actual")
    plt.ylabel("predicted")
    plt.legend()
    plt.title(title)
    plt.tight_layout()
    plt.savefig(fname, dpi=160)
    plt.close()
    print(f"✅ Saved file: {fname}")

scatter_pred_actual(Theta_X, Theta_y, np.array([c1,c2,c3]),
                    "F1 — θ̈ predicted vs actual",
                    "PAEV_TestF1_EffectiveField_PredVsActual_theta.png")

scatter_pred_actual(Kappa_X, Kappa_y, np.array([d1,d2,d3]),
                    "F1 — κ̇ predicted vs actual",
                    "PAEV_TestF1_EffectiveField_PredVsActual_kappa.png")

# quick animation (sanity)
imageio.mimsave("PAEV_TestF1_EffectiveField_Fields.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF1_EffectiveField_Fields.gif")

# ----------------------------
# save a text summary you can cite
# ----------------------------
summary = f"""
=== Test F1 — Effective Field Extraction ===

Fitted PDE (least-squares, ±1σ):
  θ̈ ≈ c1 ∇²θ + c2 κ θ + c3 ∇·(κ∇θ)
      c1 = {c1:.5f} ± {ec1:.5f}
      c2 = {c2:.5f} ± {ec2:.5f}
      c3 = {c3:.5f} ± {ec3:.5f}
  Residual variance (θ̈): σ² ≈ {sig_t:.3e}

  κ̇ ≈ d1 ∇²κ + d2 (∇θ)² + d3 κ
      d1 = {d1:.5f} ± {ed1:.5f}
      d2 = {d2:.5f} ± {ed2:.5f}
      d3 = {d3:.5f} ± {ed3:.5f}
  Residual variance (κ̇): σ² ≈ {sig_k:.3e}

Heuristic effective Lagrangian density (quadratic, units choice):
  ℒ(θ, κ) ≈ a (∂tθ)² − b (∇θ)² − e κ(∇θ)² − f κ² − g (∇κ)²
    a = {a:.3f}
    b ≈ {-0.5:.1f} * c1  → {b:.5f}
    e ≈ {-0.5:.1f} * c3  → {e:.5f}
    f ≈ {-0.5:.1f} * d3  → {f:.5f}
    g ≈ {-0.5:.1f} * d1  → {g:.5f}

Files:
  - PAEV_TestF1_EffectiveField_Fields.gif
  - PAEV_TestF1_EffectiveField_Residuals_theta.png
  - PAEV_TestF1_EffectiveField_Residuals_kappa.png
  - PAEV_TestF1_EffectiveField_PredVsActual_theta.png
  - PAEV_TestF1_EffectiveField_PredVsActual_kappa.png
"""

with open("PAEV_TestF1_EffectiveField_Summary.txt", "w", encoding="utf-8") as f:
    f.write(summary)
print("✅ Saved file: PAEV_TestF1_EffectiveField_Summary.txt")

# Final console report
print("\n=== Test F1 — Effective Field Extraction Complete ===")
print(f"θ̈ fit coeffs: c1={c1:.5f}±{ec1:.5f}, c2={c2:.5f}±{ec2:.5f}, c3={c3:.5f}±{ec3:.5f}")
print(f"κ̇ fit coeffs: d1={d1:.5f}±{ed1:.5f}, d2={d2:.5f}±{ed2:.5f}, d3={d3:.5f}±{ed3:.5f}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")