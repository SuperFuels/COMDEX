# ==========================================================
# G1 — Cosmological Constant Calibration
#   Derive an effective Λ from mean Lagrangian density ⟨ℒ⟩
#   and spectral entropy of the emergent fields.
#   - NumPy 2.0 safe (no ndarray.ptp, etc.)
#   - Stable parameters (no overflow)
#   - Bootstrap uncertainty over sliding windows
#   - Clear diagnostics & summary
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ----------------------------
# numerics & helpers
# ----------------------------
def laplacian(Z):
    # periodic 5-point stencil (grid spacing set to 1)
    return (
        -4.0 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

def grad_xy(Z):
    gx = 0.5 * (np.roll(Z, -1, 1) - np.roll(Z, 1, 1))
    gy = 0.5 * (np.roll(Z, -1, 0) - np.roll(Z, 1, 0))
    return gx, gy

def spectral_entropy(field):
    """Shannon entropy of log-power spectrum (normalized 0..1)."""
    F = np.fft.fftshift(np.fft.fft2(field))
    P = np.abs(F)**2
    Ps = P / (np.sum(P) + 1e-20)             # safe normalization
    H = -np.sum(Ps * np.log(Ps + 1e-20))     # nat units
    # normalize by maximum possible entropy on this grid: log(N)
    H_max = np.log(field.size)
    return float(H / (H_max + 1e-20))

def safe_minmax_norm(A):
    A = np.asarray(A, dtype=float)
    return (A - np.nanmin(A)) / (np.ptp(A) + 1e-20)  # np.ptp for NumPy 2.0

# ----------------------------
# simulation parameters (gentle & stable)
# ----------------------------
N = 80
steps = 320
dt = 0.02

# Effective PDE coefficients (kept mild)
c1 = 0.35    # wave speed^2 for theta
c3 = 0.08    # curvature↔phase coupling in theta
d1 = 0.15    # curvature diffusion
d2 = 0.20    # curvature drive from |∇θ|^2
d3 = -0.03   # curvature leak (gentle decay)
noise_amp = 3e-4

# Entropy→Λ mapping (dimensionless -> "Planck units" style)
beta  = 1.0     # scales energy density into Λ density
gamma = 2.0     # steeper suppression as entropy→1

# ----------------------------
# grid & initial conditions
# ----------------------------
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y, indexing="xy")

rng = np.random.default_rng(7)
theta = 0.15 * np.exp(-(X**2 + Y**2)/0.25) + 0.03 * rng.standard_normal((N, N))
theta_t = np.zeros_like(theta)
kappa = 0.08 * np.exp(-(X**2 + Y**2)/0.20) + 0.02 * rng.standard_normal((N, N))

# traces
E_trace = []
S_trace = []
Lambda_trace = []

# ----------------------------
# main evolution
# ----------------------------
for t in range(steps):
    # gradients
    gx, gy = grad_xy(theta)
    grad_theta2 = gx**2 + gy**2

    # operators
    lap_th = laplacian(theta)
    lap_k  = laplacian(kappa)

    # dynamics (semi-implicit-ish Euler; small dt keeps stable)
    theta_tt = c1 * lap_th + c3 * lap_k
    theta_t  = theta_t + dt * theta_tt
    theta    = theta   + dt * theta_t

    kappa_t = d1 * lap_k + d2 * (grad_theta2 - np.mean(grad_theta2)) + d3 * kappa
    # small zero-mean noise to prevent spectral degeneracy
    kappa_t += noise_amp * rng.standard_normal((N, N))
    kappa    = kappa + dt * kappa_t

    # effective quadratic Lagrangian density (heuristic, bounded)
    L = 0.5 * (theta_t**2 - c1 * grad_theta2) - 0.5 * c3 * kappa * grad_theta2 \
        + 0.04 * (kappa**2) - 0.02 * (grad_xy(kappa)[0]**2 + grad_xy(kappa)[1]**2)

    E_density = float(np.nanmean(L))
    # spectral entropy of the "geometric sector": use theta (could combine with kappa)
    S = spectral_entropy(theta)

    # map to Λ: positive energy density scaled by entropy complement
    Lambda_eff = beta * max(E_density, 0.0) * (1.0 - S)**gamma

    E_trace.append(E_density)
    S_trace.append(S)
    Lambda_trace.append(Lambda_eff)

E_trace = np.array(E_trace)
S_trace = np.array(S_trace)
Lambda_trace = np.array(Lambda_trace)

# ----------------------------
# bootstrap uncertainty over sliding windows
# ----------------------------
win = 40
centers = []
Lambda_win = []
for i in range(0, len(Lambda_trace) - win + 1):
    centers.append(i + win/2)
    Lambda_win.append(np.mean(Lambda_trace[i:i+win]))
centers = np.array(centers)
Lambda_win = np.array(Lambda_win)

# simple bootstrap from window means
B = 200
boot = []
for _ in range(B):
    idx = rng.integers(0, len(Lambda_win), size=len(Lambda_win))
    boot.append(np.mean(Lambda_win[idx]))
boot = np.array(boot)
lam_mean = float(np.mean(Lambda_win))
lam_lo, lam_hi = np.percentile(boot, [16, 84])

# ----------------------------
# plots
# ----------------------------
# 1) Λ(t) with windowed band
plt.figure(figsize=(8.2, 4.8))
plt.plot(Lambda_trace, lw=1.6, label="Λ(t)")
if len(Lambda_win) > 0:
    # expand window means to full length for a visual guide
    guide = np.interp(np.arange(len(Lambda_trace)), centers, Lambda_win)
    plt.plot(guide, lw=2.2, alpha=0.8, label="Λ (windowed mean)")
plt.axhline(lam_mean, color="k", ls="--", lw=1.2, label=f"Λ̄ ≈ {lam_mean:.3e}")
plt.title("G1 — Cosmological Constant Calibration (unitless)")
plt.xlabel("step")
plt.ylabel("Λ estimate")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestG1_LambdaTrace.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG1_LambdaTrace.png")

# 2) Energy & Entropy traces
fig, ax = plt.subplots(1, 1, figsize=(8.2, 4.8))
ax2 = ax.twinx()
ax.plot(E_trace, label="⟨ℒ⟩", lw=1.6, color="#1f77b4")
ax2.plot(S_trace, label="Spectral entropy (norm.)", lw=1.6, color="#2ca02c")
ax.set_title("G1 — Energy & Spectral Entropy")
ax.set_xlabel("step")
ax.set_ylabel("⟨ℒ⟩")
ax2.set_ylabel("entropy")
lns = ax.get_lines() + ax2.get_lines()
labs = [l.get_label() for l in lns]
ax.legend(lns, labs, loc="best")
plt.tight_layout()
plt.savefig("PAEV_TestG1_EnergyEntropy.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG1_EnergyEntropy.png")

# 3) Bootstrap histogram
plt.figure(figsize=(6.2, 4.6))
plt.hist(boot, bins=40, alpha=0.85)
plt.axvline(lam_mean, color="k", lw=1.5, ls="--", label=f"Λ̄={lam_mean:.3e}")
plt.axvline(lam_lo, color="k", lw=1.0, ls=":")
plt.axvline(lam_hi, color="k", lw=1.0, ls=":")
plt.title("G1 — Bootstrap Λ distribution (window means)")
plt.xlabel("Λ")
plt.ylabel("count")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestG1_LambdaHistogram.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG1_LambdaHistogram.png")

# ----------------------------
# summary
# ----------------------------
summary = f"""
=== Test G1 — Cosmological Constant Calibration ===

Grid: {N}x{N}, steps={steps}, dt={dt}
Coeffs: c1={c1}, c3={c3}, d1={d1}, d2={d2}, d3={d3}
Noise amplitude: {noise_amp}

Mapping: Λ = β * max(⟨ℒ⟩,0) * (1 - S)^γ
  β={beta}, γ={gamma}
Where S is normalized spectral entropy of θ's spectrum.

Results:
  Λ̄ (window-mean)  = {lam_mean:.6e}
  68% CI (bootstrap)= [{lam_lo:.6e}, {lam_hi:.6e}]
  Final Λ(t)        = {Lambda_trace[-1]:.6e}
  Final ⟨ℒ⟩         = {E_trace[-1]:.6e}
  Final entropy S   = {S_trace[-1]:.6e}

Files:
  - PAEV_TestG1_LambdaTrace.png
  - PAEV_TestG1_EnergyEntropy.png
  - PAEV_TestG1_LambdaHistogram.png
"""
Path("PAEV_TestG1_Summary.txt").write_text(summary.strip() + "\n", encoding="utf-8")
print("✅ Saved file: PAEV_TestG1_Summary.txt")

print("\n=== Test G1 — Cosmological Constant Calibration Complete ===")
print(f"Λ̄ ≈ {lam_mean:.3e}  (68% CI: {lam_lo:.3e} … {lam_hi:.3e})")
print(f"Final ⟨ℒ⟩ = {E_trace[-1]:.3e}, Final S = {S_trace[-1]:.3e}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")