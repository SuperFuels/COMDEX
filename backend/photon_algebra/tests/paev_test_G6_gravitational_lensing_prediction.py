# ==========================================================
# G6 — Gravitational Lensing & Phase-Shift Prediction
#   Predict light deflection and interference fringe shift
#   under a localized curvature (kappa) "lens".
#   Outputs compare measured deflection to a GR-like model
#   in normalized units and tracks phase/entropy stability.
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

rng = np.random.default_rng(42)

# ----------------------------
# helpers (periodic)
# ----------------------------
def laplacian(Z):
    return (-4.0*Z
            + np.roll(Z,1,0) + np.roll(Z,-1,0)
            + np.roll(Z,1,1) + np.roll(Z,-1,1))

def grad_xy(Z):
    gx = 0.5*(np.roll(Z,-1,1) - np.roll(Z,1,1))
    gy = 0.5*(np.roll(Z,-1,0) - np.roll(Z,1,0))
    return gx, gy

def spectral_entropy(field):
    F = np.fft.fftshift(np.fft.fft2(field))
    P = np.abs(F)**2
    s = np.sum(P)
    if not np.isfinite(s) or s <= 0:
        return 0.0
    p = P / s
    # guard against log(0)
    with np.errstate(divide='ignore', invalid='ignore'):
        H = -np.nansum(p * np.log(p + 1e-30))
    # normalize by log of number of modes
    return float(H / np.log(p.size + 1e-12))

def clamp_nan(x):
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    x = np.clip(x, -1e6, 1e6)
    return x

# ----------------------------
# grid & parameters
# ----------------------------
N = 96
steps = 320
dt = 0.02

# wave/interaction constants (stable regime)
c1 = 0.50          # phase stiffness
c2 = 0.00          # (unused here)
chi = 0.12         # coupling to curvature
gamma = 0.02       # mild damping on psi
eta_k = 0.08       # curvature relaxation
noise_k = 5e-5     # small stochastic drive

x = np.linspace(-1, 1, N, endpoint=False)
y = np.linspace(-1, 1, N, endpoint=False)
X, Y = np.meshgrid(x, y)

# ----------------------------
# initial fields
# ----------------------------
# complex photon field psi = A * exp(i*theta)
beam_w = 0.30
theta0 = np.exp(-((X+0.55)**2 + (Y)**2)/(2*beam_w**2)) * 1.0  # right-moving phase bump
psi = np.exp(1j*theta0) * (0.9 + 0.1*rng.standard_normal((N,N)))
psi_t = np.zeros_like(psi)

# localized curvature "lens"
lens_w = 0.20
lens_amp = 1.0
kappa = lens_amp * np.exp(-(X**2 + Y**2)/(2*lens_w**2))
# slight roughness
kappa += 0.02*rng.standard_normal((N,N))

# two-slit phase mask (Mach–Zehnder analog in phase)
slit_sep = 0.35
slit_w   = 0.06
phase_mask = np.exp(1j*( np.exp(-((Y-slit_sep/2)/slit_w)**2)*0.6
                        + np.exp(-((Y+slit_sep/2)/slit_w)**2)*0.6 ))

# ----------------------------
# storage & movie
# ----------------------------
E_trace, S_trace, defl_pred_trace, defl_meas_trace = [], [], [], []
frames = []

# analytic GR-like small-angle deflection (normalized):
# alpha_GR ~ A * ∇Phi; here Phi ~ kappa, so we take
# alpha_pred ∝ chi * |∇kappa|_peak
gkx, gky = grad_xy(kappa)
alpha_pred = chi * np.sqrt(np.max(gkx**2 + gky**2))
alpha_pred = float(alpha_pred)

# ----------------------------
# evolution
# ----------------------------
for t in range(steps):
    # curvature relaxes slowly (kept near static lens)
    lapK = laplacian(kappa)
    kappa = kappa + dt*(eta_k*lapK) + noise_k*rng.standard_normal((N,N))
    kappa = clamp_nan(kappa)

    # phase-like evolution of psi (complex wave with curvature coupling)
    # wave equation in split form on Re/Im using laplacian of psi and coupling to kappa
    lapPsi = laplacian(psi)
    # coupling term: curvature modulates local phase velocity
    psi_tt = c1*lapPsi - gamma*psi_t + 1j*chi*kappa*psi

    psi_t = psi_t + dt*psi_tt
    psi   = psi   + dt*psi_t
    # renormalize occasionally to avoid blow-up
    if t % 8 == 0:
        amp = np.abs(psi)
        m = np.nanmean(amp)
        if np.isfinite(m) and m > 0:
            psi /= (m + 1e-12)

    # apply phase mask midway to form interference
    if t == steps//2:
        psi *= phase_mask

    # diagnostics
    intensity = np.abs(psi)**2
    # center-of-mass shift (x-direction) as deflection proxy
    I = clamp_nan(intensity)
    I_sum = np.sum(I)
    if I_sum <= 0 or not np.isfinite(I_sum):
        x_cm = 0.0
    else:
        x_cm = float(np.sum(I * X) / I_sum)
    defl_meas = abs(x_cm)  # magnitude
    defl_meas_trace.append(defl_meas)
    defl_pred_trace.append(alpha_pred)

    # simple energy proxy and spectral entropy of phase
    # use arg(psi) as phase field
    theta = np.angle(psi)
    gx, gy = grad_xy(theta)
    L = 0.5*(np.abs(psi_t)**2).mean() + 0.5*c1*((gx**2 + gy**2).mean()) - 0.5*chi*(kappa*(gx**2 + gy**2)).mean()
    E_trace.append(float(np.nan_to_num(np.real(L), nan=0.0)))
    S_trace.append(spectral_entropy(theta))

    # movie frame every ~12 steps
    if t % 12 == 0:
        fig, ax = plt.subplots(1,2, figsize=(7.8,3.4))
        ax[0].imshow(np.real(psi), cmap="twilight_shifted")
        ax[0].set_title(f"Re(ψ) @ step {t}")
        ax[0].axis("off")
        ax[1].imshow(kappa, cmap="magma")
        ax[1].set_title("κ lens")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.asarray(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# plots
# ----------------------------
# 1) Energy / Entropy / Deflection
fig, ax1 = plt.subplots(figsize=(7.6,4.2))
ax1.plot(E_trace, label="⟨ℒ⟩ (proxy)", lw=2)
ax1.set_xlabel("step")
ax1.set_ylabel("energy proxy")
ax2 = ax1.twinx()
ax2.plot(S_trace, color="seagreen", label="spectral entropy (norm.)", lw=2)
ax2.plot(defl_meas_trace, color="darkorange", lw=2, alpha=0.9, label="deflection (meas.)")
ax2.hlines(alpha_pred, 0, len(S_trace)-1, colors="crimson", linestyles="--", label="deflection (pred.)")
ax2.set_ylabel("entropy / deflection")
ax1.set_title("G6 — Energy, Entropy, and Deflection")
ax1.legend(loc="upper left")
ax2.legend(loc="upper right")
plt.tight_layout()
plt.savefig("PAEV_TestG6_Lensing_Trace.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG6_Lensing_Trace.png")

# 2) Interference pattern snapshot (intensity)
plt.figure(figsize=(6.2,5.3))
plt.imshow(np.log10(np.abs(np.fft.fftshift(np.fft.fft2(psi)))**2 + 1e-8), cmap="magma")
plt.colorbar(label="log10|Ψ(k)|²")
plt.title("G6 — ψ Spectrum (interference signature)")
plt.tight_layout()
plt.savefig("PAEV_TestG6_PsiSpectrum.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG6_PsiSpectrum.png")

# 3) Final fields side-by-side
fig, ax = plt.subplots(1,2, figsize=(8.2,3.6))
ax[0].imshow(np.real(psi), cmap="twilight_shifted")
ax[0].set_title(f"Re(ψ) — final")
ax[0].axis("off")
ax[1].imshow(kappa, cmap="magma")
ax[1].set_title("κ lens (final)")
ax[1].axis("off")
plt.tight_layout()
plt.savefig("PAEV_TestG6_FinalFields.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG6_FinalFields.png")

# 4) Movie
imageio.mimsave("PAEV_TestG6_Lensing_Propagation.gif", frames, fps=12)
print("✅ Saved animation to: PAEV_TestG6_Lensing_Propagation.gif")

# ----------------------------
# console summary
# ----------------------------
defl_meas_final = defl_meas_trace[-1] if defl_meas_trace else 0.0
print("\n=== Test G6 — Gravitational Lensing & Phase-Shift Prediction Complete ===")
print(f"⟨ℒ⟩ final (proxy) = {E_trace[-1]:.6e}")
print(f"S (final)         = {S_trace[-1]:.6e}")
print(f"Deflection (pred) = {alpha_pred:.6e}")
print(f"Deflection (meas) = {defl_meas_final:.6e}")
print("Perturbation mode: ON")
print("\nAll output files saved in working directory.")
print("----------------------------------------------------------")