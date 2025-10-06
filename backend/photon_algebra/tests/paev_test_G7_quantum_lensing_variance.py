# ==========================================================
# G7 — Quantum Lensing Variance Calibration
#   Measures phase-variance dynamics Δφ and its correlation
#   with curvature κ under a weak-lensing potential. Also
#   tracks spectral entropy stability for ψ.
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ---------- numerics & helpers ----------

def laplacian(Z):
    # 5-point stencil (unit grid); numerically stable, no dx factor
    return (-4.0 * Z
            + np.roll(Z,  1, 0) + np.roll(Z, -1, 0)
            + np.roll(Z,  1, 1) + np.roll(Z, -1, 1))

def spectral_entropy(field):
    # robust spectral entropy (2D PSD)
    F = np.fft.fft2(field)
    P = np.abs(F) ** 2
    P = np.fft.fftshift(P)
    s = np.sum(P)
    if not np.isfinite(s) or s <= 0:
        return 0.0
    p = P / (s + 1e-12)
    # avoid log(0) by masking zeros
    mask = p > 0
    H = -np.sum(p[mask] * np.log(p[mask]))
    # normalize by max entropy = log(N) for N bins
    Hn = H / np.log(p.size)
    return float(np.clip(Hn, 0.0, 1.0))

def zscore_corr(a, b):
    # correlation with nan/zero-variance safety
    am = np.nanmean(a); bm = np.nanmean(b)
    asd = np.nanstd(a); bsd = np.nanstd(b)
    if asd <= 1e-12 or bsd <= 1e-12 or not np.isfinite(asd*bsd):
        return 0.0
    return float(np.nanmean(((a - am) / asd) * ((b - bm) / bsd)))

# ---------- parameters ----------
N = 96
steps = 320
dt = 0.05

# weak, stable couplings
c_psi = 0.35       # ψ diffusion-like coupling
c_k   = 0.25       # κ diffusion
chi   = 0.08       # ψ↔κ coupling (lens strength)
gamma = 0.02       # mild ψ damping
eta   = 0.03       # κ relaxation
noise_amp = 1e-4   # tiny drive to break symmetry

# ---------- grids & initial conditions ----------
x = np.linspace(-2.2, 2.2, N)
y = np.linspace(-2.2, 2.2, N)
X, Y = np.meshgrid(x, y)
R2 = X**2 + Y**2

rng = np.random.default_rng(7)

# Complex field ψ = A * exp(i φ)
A0 = np.exp(-R2 / 1.1) * (1.0 + 0.02 * rng.standard_normal((N, N)))
phi0 = 0.12 * np.exp(-R2 / 0.8) + 0.03 * rng.standard_normal((N, N))
psi = A0 * np.exp(1j * phi0)

# Curvature lens κ — centered bump + soft noise
kappa = 0.8 * np.exp(-R2 / 1.5) + 0.03 * rng.standard_normal((N, N))

# ---------- traces ----------
energy_trace = []
entropy_trace = []
varphi_trace = []
corr_trace = []
pred_deflection_trace = []   # simple proxy, optional

frames = []

print("💥 Perturbation mode enabled — injecting Gaussian phase/curvature pulse.")

# ---------- evolution ----------
for t in range(steps):
    # separate amplitude/phase each step
    A = np.abs(psi)
    phi = np.angle(psi)

    # ψ update: real+imag via Laplacian on ψ, plus curvature-coupled phase shift
    lap_psi = laplacian(psi)
    # curvature -> phase refraction: i*chi*kappa*psi; include mild damping on ψ
    psi_t = c_psi * lap_psi + 1j * chi * kappa * psi - gamma * psi
    psi = psi + dt * psi_t

    # κ update: diffusion + sourced by local phase gradients (∇φ)^2, relax to 0
    # compute stable phase gradients via unwrap in each axis
    phi_x = np.unwrap(phi, axis=1)
    phi_y = np.unwrap(phi, axis=0)
    gpx = 0.5 * (np.roll(phi_x, -1, 1) - np.roll(phi_x, 1, 1))
    gpy = 0.5 * (np.roll(phi_y, -1, 0) - np.roll(phi_y, 1, 0))
    gradphi2 = gpx**2 + gpy**2

    kappa_t = c_k * laplacian(kappa) + 0.15 * (gradphi2 - np.nanmean(gradphi2)) - eta * kappa
    # tiny stochastic drive
    kappa_t += noise_amp * rng.standard_normal((N, N))
    kappa = kappa + dt * kappa_t

    # ---------- diagnostics ----------
    # energy proxy: mean(|∇ψ|^2) + chi * <kappa*|ψ|^2>
    # compute |∇ψ| via central differences on real/imag
    pr = np.real(psi); pi = np.imag(psi)
    dprx = 0.5 * (np.roll(pr, -1, 1) - np.roll(pr, 1, 1))
    dpry = 0.5 * (np.roll(pr, -1, 0) - np.roll(pr, 1, 0))
    dpix = 0.5 * (np.roll(pi, -1, 1) - np.roll(pi, 1, 1))
    dpiy = 0.5 * (np.roll(pi, -1, 0) - np.roll(pi, 1, 0))
    gradpsi2 = dprx**2 + dpry**2 + dpix**2 + dpiy**2
    E = np.nanmean(gradpsi2) + chi * np.nanmean(kappa * (A**2))
    energy_trace.append(float(E))

    # spectral entropy of ψ magnitude (more stable than raw complex)
    S = spectral_entropy(A)
    entropy_trace.append(S)

    # phase variance (quantum lensing variance)
    dphi = phi - np.nanmean(phi)
    var_phi = float(np.nanmean(dphi**2))
    varphi_trace.append(var_phi)

    # correlation between Δφ and κ (coherence of quantum lensing)
    corr = zscore_corr(dphi, kappa)
    corr_trace.append(corr)

    # a tiny analytic deflection proxy: <|∇φ|>/const (kept for continuity with G6)
    defl_pred = float(np.nanmean(np.sqrt(gradphi2))) * 0.01
    pred_deflection_trace.append(defl_pred)

    # ---------- make a few frames ----------
    if t % 20 == 0 or t == steps - 1:
        fig, ax = plt.subplots(1, 2, figsize=(8.4, 3.6))
        im0 = ax[0].imshow(np.real(psi), cmap="twilight")
        ax[0].set_title(f"Re(ψ) — step {t}")
        ax[0].axis("off")
        im1 = ax[1].imshow(kappa, cmap="magma")
        ax[1].set_title("κ lens")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ---------- plots ----------
# 1) Variance, Energy, Entropy, Correlation traces
taxis = np.arange(steps)

fig, ax1 = plt.subplots(figsize=(8.6, 4.6))
ax1.plot(taxis, energy_trace, label="⟨ℒ⟩ proxy", color="steelblue")
ax1.plot(taxis, varphi_trace, label="Var(Δφ)", color="purple", alpha=0.75)
ax1.set_xlabel("step")
ax1.set_ylabel("energy / variance")
ax2 = ax1.twinx()
ax2.plot(taxis, entropy_trace, label="spectral entropy (norm.)", color="seagreen")
ax2.plot(taxis, corr_trace, label="corr(Δφ, κ)", color="orange")
ax2.set_ylabel("entropy / correlation")
ax1.legend(loc="upper left")
ax2.legend(loc="upper right")
ax1.set_title("G7 — Variance, Entropy, and Phase–Curvature Coherence")
plt.tight_layout()
plt.savefig("PAEV_TestG7_VarianceTrace.png", dpi=140)
plt.close()
print("✅ Saved file: PAEV_TestG7_VarianceTrace.png")

# 2) Phase–Curvature Correlation vs Entropy (phase portrait)
plt.figure(figsize=(6.2, 5.1))
plt.plot(entropy_trace, corr_trace, color="darkorange")
plt.xlabel("spectral entropy (ψ magnitude)")
plt.ylabel("corr(Δφ, κ)")
plt.title("G7 — Phase–Curvature Coherence Portrait")
plt.grid(alpha=0.25)
plt.tight_layout()
plt.savefig("PAEV_TestG7_PhaseCurvatureCorr.png", dpi=140)
plt.close()
print("✅ Saved file: PAEV_TestG7_PhaseCurvatureCorr.png")

# 3) Spectral stability — log power of ψ at final step
F = np.fft.fftshift(np.fft.fft2(np.abs(psi)))
P = np.log10(np.maximum(np.abs(F)**2, 1e-12))
plt.figure(figsize=(6.3, 5.6))
im = plt.imshow(P, cmap="magma")
plt.colorbar(im, label="log10 |Ψ(k)|²")
plt.title("G7 — ψ Spectrum (final)")
plt.tight_layout()
plt.savefig("PAEV_TestG7_SpectralStability.png", dpi=140)
plt.close()
print("✅ Saved file: PAEV_TestG7_SpectralStability.png")

# 4) Animation
imageio.mimsave("PAEV_TestG7_PsiVariance.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestG7_PsiVariance.gif")

# ---------- console summary ----------
E_final = float(energy_trace[-1])
S_final = float(entropy_trace[-1])
V_final = float(varphi_trace[-1])
C_final = float(corr_trace[-1])
D_final = float(pred_deflection_trace[-1])

print("\n=== Test G7 — Quantum Lensing Variance Calibration Complete ===")
print(f"⟨ℒ⟩ (proxy) final = {E_final:.6e}")
print(f"S (final)         = {S_final:.6f}")
print(f"Var(Δφ) (final)   = {V_final:.6e}")
print(f"corr(Δφ, κ) final = {C_final:.3f}")
print(f"deflection (pred) = {D_final:.6e}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")