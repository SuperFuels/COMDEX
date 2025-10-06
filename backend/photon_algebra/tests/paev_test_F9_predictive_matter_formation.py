# ==========================================================
# Test F9 — Predictive Matter Formation
#   Goal: add a "matter" scalar ψ coupled to (θ, κ),
#         watch clumping/structure emerge, track spectra,
#         clump counts, and ψ–κ correlation.
#
#   ψ obeys a stabilized Klein–Gordon-like flow with
#   curvature-modulated mass and weak self-interaction:
#       ψ̈ = u1 ∇²ψ - μ_eff^2 ψ - λ ψ³ + β κ + ξ θ
#   with μ_eff^2 = μ0^2 + aκ κ + aθ θ²  (all small & stable)
#
#   θ, κ reuse your stable F6/F7-style updates (safe dt,
#   small couplings, diffusion + relaxation + k–θ coupling).
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# helpers (NumPy 2.x-safe)
# ----------------------------
def laplacian(Z):
    # 5-point periodic stencil (grid spacing = 1)
    return (-4.0 * Z
            + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
            + np.roll(Z, 1, 1) + np.roll(Z, -1, 1))

def grad_xy(Z):
    gx = 0.5 * (np.roll(Z, -1, 1) - np.roll(Z, 1, 1))
    gy = 0.5 * (np.roll(Z, -1, 0) - np.roll(Z, 1, 0))
    return gx, gy

def spectral_entropy(field):
    F = np.fft.fftshift(np.abs(np.fft.fft2(field))**2)
    s = np.sum(F)
    if not np.isfinite(s) or s <= 0:
        return 0.0
    p = F / s
    # safe entropy: sum p log p where p>0
    p = p[p > 0]
    H = -np.sum(p * np.log(p + 1e-20))
    # normalize by log(N^2) so 0..1-ish
    nrm = np.log(field.size + 1e-20)
    return float(H / (nrm if nrm > 0 else 1.0))

def soft_clip(x, limit=5.0):
    # symmetric limiter to avoid blow-ups
    return limit * np.tanh(x / max(limit, 1e-8))

def safe_imshow(ax, Z, cmap="magma", vmin=None, vmax=None, title=None):
    if vmin is None: vmin = float(np.nanpercentile(Z, 1))
    if vmax is None: vmax = float(np.nanpercentile(Z, 99))
    im = ax.imshow(Z, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title or "")
    ax.set_xticks([]); ax.set_yticks([])
    return im

# --- tiny connected-component counter for ψ clumps (4-neighborhood) ---
def count_blobs(binary):
    visited = np.zeros_like(binary, dtype=bool)
    H, W = binary.shape
    def neighbors(i,j):
        for di, dj in ((1,0),(-1,0),(0,1),(0,-1)):
            ni, nj = (i+di) % H, (j+dj) % W  # periodic
            yield ni, nj
    count = 0
    for i in range(H):
        for j in range(W):
            if binary[i,j] and not visited[i,j]:
                count += 1
                # BFS
                stack = [(i,j)]
                visited[i,j] = True
                while stack:
                    ci, cj = stack.pop()
                    for ni, nj in neighbors(ci,cj):
                        if binary[ni,nj] and not visited[ni,nj]:
                            visited[ni,nj] = True
                            stack.append((ni,nj))
    return count

# ----------------------------
# simulation parameters
# ----------------------------
N         = 80
steps     = 320
dt        = 0.02
rng       = np.random.default_rng(7)

# Field initial conditions
x = np.linspace(-1, 1, N); X, Y = np.meshgrid(x, x)
R2 = X**2 + Y**2

theta   = 0.15 * np.exp(-R2/0.18) + 0.02 * rng.standard_normal((N,N))
theta_t = np.zeros_like(theta)

kappa   = 0.10 * np.exp(-R2/0.12) + 0.02 * rng.standard_normal((N,N))
psi     = 0.05 * np.exp(-R2/0.1)  + 0.01 * rng.standard_normal((N,N))
psi_t   = np.zeros_like(psi)

# Couplings (small, stable)
c1  = 0.75      # θ wave speed^2 (on laplacian)
chi = 0.14      # θ–κ cross-coupling
gamma_theta = 0.018  # θ damping
zeta_k  = 0.035      # κ diffusion
eta_k   = 0.06       # κ relaxation
drive_k = 0.10       # κ driven by |∇θ|^2

# Matter ψ parameters
u1  = 0.55       # ψ "stiffness" (laplacian coeff)
mu0 = 0.15       # base mass
a_k = 0.20       # curvature-to-mass coupling
a_t = 0.08       # θ^2-to-mass coupling
lam = 0.02       # weak self-interaction
beta= 0.05       # κ source into ψ
xi  = 0.02       # θ source into ψ
damp_psi = 0.02  # ψ damping

noise_k = 2e-4   # small noise to avoid trapping

# Diagnostics storage
E_trace, corr_trace, H_trace, clump_trace = [], [], [], []
frames = []

# Threshold for ψ clumps (adaptive to σ)
def clump_threshold(phi):
    s = float(np.nanstd(phi))
    m = float(np.nanmean(phi))
    return m + 1.5*s

# ----------------------------
# main loop
# ----------------------------
for t in range(steps):

    # --- θ update (wave-ish with κ feedback) ---
    lap_th = laplacian(theta)
    gx, gy = grad_xy(theta)
    div_kgrad = (np.roll(kappa*gx, -1, 1) - np.roll(kappa*gx, 1, 1)) * 0.5 \
              + (np.roll(kappa*gy, -1, 0) - np.roll(kappa*gy, 1, 0)) * 0.5
    theta_tt = c1 * lap_th + chi * div_kgrad - gamma_theta * theta_t
    theta_t  = soft_clip(theta_t + dt * theta_tt,  limit=2.0)
    theta    = soft_clip(theta   + dt * theta_t,   limit=2.0)

    # --- κ update (diffusion + relaxation + |∇θ|^2 drive) ---
    g2 = gx*gx + gy*gy
    kappa_t = zeta_k * laplacian(kappa) - eta_k * kappa + drive_k * (g2 - float(np.nanmean(g2)))
    kappa_t += noise_k * rng.standard_normal((N,N))
    kappa    = soft_clip(kappa + dt * kappa_t, limit=2.0)

    # --- ψ update (stabilized KG-like with curvature mass) ---
    mu_eff2 = mu0*mu0 + a_k * kappa + a_t * (theta*theta)
    mu_eff2 = np.clip(mu_eff2, 0.0, 1.0)  # keep positive/small
    psi_tt  = u1 * laplacian(psi) - mu_eff2 * psi - lam*(psi**3) + beta*kappa + xi*theta - damp_psi*psi_t
    psi_t   = soft_clip(psi_t + dt * psi_tt, limit=2.0)
    psi     = soft_clip(psi   + dt * psi_t,  limit=2.0)

    # --- Lagrangian density (heuristic, positive-definite-ish) ---
    gkx, gky   = grad_xy(kappa)
    gpx, gpy   = grad_xy(psi)
    grad_theta2= gx*gx + gy*gy
    grad_k2    = gkx*gkx + gky*gky
    grad_p2    = gpx*gpx + gpy*gpy

    L = 0.5*(theta_t**2 + psi_t**2) \
        - 0.35*grad_theta2 - 0.015*grad_k2 - 0.25*grad_p2 \
        - 0.04*(kappa**2)  - 0.5*mu_eff2*(psi**2) - 0.01*(psi**4) \
        - 0.04*kappa*grad_theta2 - 0.03*kappa*(psi**2)

    # --- Diagnostics ---
    E_trace.append(float(np.nanmean(L)))
    corr_trace.append(float(np.nanmean(psi * kappa)))
    H_trace.append(spectral_entropy(psi))

    thr = clump_threshold(psi)
    blobs = count_blobs(psi > thr)
    clump_trace.append(int(blobs))

    # --- GIF frames (sparse) ---
    if t % 20 == 0 or t == steps-1:
        fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.2))
        safe_imshow(ax[0], psi,   cmap="magma", title=f"ψ @ step {t}")
        safe_imshow(ax[1], kappa, cmap="magma", title="κ field")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# Plots & outputs
# ----------------------------
# 1) Energy / corr / entropy / clumps trace
tarr = np.arange(steps)

plt.figure(figsize=(8.6,4.6))
plt.title("F9 — Matter Formation: Energy, Corr., Entropy, Clumps")
plt.plot(tarr, E_trace,      label="⟨ℒ⟩")
plt.plot(tarr, corr_trace,   label="⟨ψ·κ⟩")
# normalize entropy & clumps for common axis (visual only)
Hn = (np.array(H_trace) - np.min(H_trace)) / (np.ptp(H_trace)+1e-12)
Cn = (np.array(clump_trace) - np.min(clump_trace)) / (max(np.ptp(clump_trace),1)+1e-12)
plt.plot(tarr, Hn,           label="spectral entropy (norm.)")
plt.plot(tarr, Cn,           label="# clumps (norm.)", linestyle="--")
plt.legend()
plt.xlabel("step"); plt.tight_layout()
plt.savefig("PAEV_TestF9_Matter_EnergyTrace.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF9_Matter_EnergyTrace.png")

# 2) ψ power spectrum (log power)
Fpsi = np.fft.fftshift(np.abs(np.fft.fft2(psi))**2)
Fpsi = np.log10(np.maximum(Fpsi, 1e-14))
plt.figure(figsize=(5.6,5.2))
plt.title("F9 — ψ Field Spectrum (log power)")
im = plt.imshow(Fpsi, cmap="magma")
plt.colorbar(im, label="log |ψ(k)|²")
plt.xticks([]); plt.yticks([])
plt.tight_layout()
plt.savefig("PAEV_TestF9_Matter_Spectrum.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF9_Matter_Spectrum.png")

# 3) Clump count evolution
plt.figure(figsize=(6.4,4.4))
plt.title("F9 — Matter Clump Count")
plt.plot(tarr, clump_trace)
plt.xlabel("step"); plt.ylabel("# clumps (ψ > μ+1.5σ)")
plt.tight_layout()
plt.savefig("PAEV_TestF9_Matter_Clumps.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF9_Matter_Clumps.png")

# 4) Phase portrait: entropy vs ψ·κ (organization curve)
plt.figure(figsize=(6.2,4.8))
plt.title("F9 — Phase Portrait (Entropy vs ⟨ψ·κ⟩)")
plt.plot(H_trace, corr_trace, color="orange")
plt.xlabel("spectral entropy(ψ)"); plt.ylabel("⟨ψ·κ⟩")
plt.tight_layout()
plt.savefig("PAEV_TestF9_Matter_PhasePortrait.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF9_Matter_PhasePortrait.png")

# 5) Final snapshot (ψ & κ)
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.2))
safe_imshow(ax[0], psi,   cmap="magma", title=f"ψ field @ step {steps-1}")
safe_imshow(ax[1], kappa, cmap="magma", title="κ field")
plt.tight_layout()
plt.savefig("PAEV_TestF9_Matter_FinalFields.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF9_Matter_FinalFields.png")

# GIF
imageio.mimsave("PAEV_TestF9_Matter_Formation.gif", frames, fps=12)
print("✅ Saved animation to: PAEV_TestF9_Matter_Formation.gif")

# Console summary
print("\n=== Test F9 — Predictive Matter Formation Complete ===")
print(f"⟨ℒ⟩ final = {np.array(E_trace)[-1]:.4e}")
print(f"⟨ψ·κ⟩ final = {np.array(corr_trace)[-1]:.4e}")
print(f"Spectral entropy(ψ) final = {np.array(H_trace)[-1]:.4e}")
print(f"Clumps(final) = {clump_trace[-1]}")
print("Perturbation mode: ON")
print("\nAll output files saved in working directory.")
print("----------------------------------------------------------")