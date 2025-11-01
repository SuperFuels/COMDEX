# ==========================================================
# G5 - Planck-Scale Unification Calibration
#   Curvature-Information density -> (G, ħ) in normalized units
#   Robust to NumPy 2.0; overflow-safe; matches COMDEX tracing style
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# numerics & helpers (stable)
# ----------------------------
def laplacian(Z):
    # 5-point stencil without explicit dx (absorbed in units)
    return (-4.0 * Z
            + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
            + np.roll(Z, 1, 1) + np.roll(Z, -1, 1))

def spectral_entropy(field):
    # power spectrum entropy (normalized 0..1), NumPy 2.0 safe
    F = np.fft.fft2(field)
    P = np.abs(F)**2
    s = np.sum(P)
    if not np.isfinite(s) or s <= 0:
        return 0.0
    p = P / s
    p = np.clip(p, 1e-20, 1.0)          # avoid log(0)
    H = -np.sum(p * np.log(p))
    Hmax = np.log(p.size)
    return float(H / Hmax)

def safe_mean(x):
    return float(np.nanmean(np.asarray(x, dtype=np.float64)))

def safe_std(x):
    return float(np.nanstd(np.asarray(x, dtype=np.float64)))

# ----------------------------
# simulation parameters
# ----------------------------
N = 84
steps = 320
dt = 0.02
rng = np.random.default_rng(7)

# gentle/stable coefficients (aligned with your F-series)
c1 = 0.85        # wave/curvature stiffness
c2 = 0.10        # cross-coupling (θ ↔ κ)
d1 = 0.05        # curvature diffusion
gamma = 0.02     # θ damping
eta = 0.015      # κ damping
noise_amp = 1e-3 # small stochastic drive

# ----------------------------
# initial fields
# ----------------------------
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

theta = 0.10 * np.exp(-((X**2 + Y**2)/0.25)) + 0.02 * rng.standard_normal((N, N))
theta_t = np.zeros_like(theta)
kappa = 0.08 * np.exp(-((X**2 + Y**2)/0.18)) + 0.02 * rng.standard_normal((N, N))

# ----------------------------
# storage
# ----------------------------
E_trace, S_trace, I_trace = [], [], []
G_eff_trace, hbar_eff_trace = [], []
Lambda_proxy_trace = []
frames = []

# scaling knobs (heuristic -> dimensionless "Planck" units)
# We treat information density I ~ ⟨(∇θ)^2⟩ + ε ⟨(∇κ)^2⟩
# and curvature density K ~ ⟨κ^2⟩ + δ ⟨(∇κ)^2⟩
eps_grad = 0.5
delta_curv = 0.25

# calibration constants (set magnitude; you can sweep later)
# target dimensionless Planck density ρ_P^* ~ 1 by construction
alpha_I = 1.0
alpha_K = 1.0

# mapping:
#   ρ_P ~ alpha_I * I * alpha_K * K
#   G_eff ~ 1 / sqrt(ρ_P + ε)     (so higher info*curv -> stronger "quantum gravity")
#   ħ_eff ~ sqrt(I / (K + ε))     (information vs curvature balance)
#   Λ_proxy ~ K - I (qualitative check vs G1)
eps = 1e-12

# ----------------------------
# evolve & estimate effective (G, ħ)
# ----------------------------
for t in range(steps):
    # core PDE (tamed, semi-linear)
    lap_th = laplacian(theta)
    lap_ka = laplacian(kappa)

    # second-order θ with damping and curvature feedback
    theta_tt = c1 * lap_th + c2 * lap_ka - gamma * theta_t
    theta_t  = theta_t + dt * theta_tt
    theta    = theta   + dt * theta_t

    # curvature relaxes + diffuse + driven by θ gradients
    gx = 0.5 * (np.roll(theta, -1, 1) - np.roll(theta, 1, 1))
    gy = 0.5 * (np.roll(theta, -1, 0) - np.roll(theta, 1, 0))
    grad2_theta = gx**2 + gy**2

    kappa_t = d1 * lap_ka - eta * kappa + 0.20 * (grad2_theta - safe_mean(grad2_theta))
    kappa_t += noise_amp * rng.standard_normal((N, N))
    kappa = kappa + dt * kappa_t

    # gentle clipping to prevent numerical blow-ups
    theta = np.tanh(theta) * 5.0
    kappa = np.tanh(kappa) * 5.0
    theta_t = np.clip(theta_t, -10, 10)

    # diagnostics: energy-like density and entropies
    grad_kx = 0.5 * (np.roll(kappa, -1, 1) - np.roll(kappa, 1, 1))
    grad_ky = 0.5 * (np.roll(kappa, -1, 0) - np.roll(kappa, 1, 0))
    grad2_kappa = grad_kx**2 + grad_ky**2

    # Lagrangian proxy (positive-definite-ish for stability)
    L = 0.5 * (theta_t**2 + 0.5*c1*(gx**2 + gy**2)) + 0.25*c2*(kappa**2) + 0.05*grad2_kappa
    E_trace.append(safe_mean(L))

    S_theta = spectral_entropy(theta)
    S_kappa = spectral_entropy(kappa)
    S = 0.5 * (S_theta + S_kappa)
    S_trace.append(S)

    # information & curvature densities
    I = alpha_I * safe_mean(grad2_theta + eps_grad*grad2_kappa)
    K = alpha_K * safe_mean(kappa**2 + delta_curv*grad2_kappa)
    I_trace.append(I)

    rho_P = max(I*K, eps)
    G_eff = 1.0 / np.sqrt(rho_P)
    hbar_eff = np.sqrt(I / (K + eps))
    G_eff_trace.append(G_eff)
    hbar_eff_trace.append(hbar_eff)

    # Λ consistency proxy
    Lambda_proxy_trace.append(K - I)

    # frames every ~18 steps
    if t % 18 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.2))
        im0 = ax[0].imshow(theta, cmap="twilight", interpolation="nearest")
        ax[0].set_title(f"θ field @ step {t}")
        ax[0].axis("off")
        im1 = ax[1].imshow(kappa, cmap="magma", interpolation="nearest")
        ax[1].set_title("κ field")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# plots
# ----------------------------
# 1) Energy / Entropy / Effective constants trace
fig, ax = plt.subplots(1, 1, figsize=(8, 4.6))
ax.plot(E_trace, label="⟨L⟩", lw=2)
ax.plot(S_trace, label="spectral entropy (norm.)", lw=2)
ax2 = ax.twinx()
ax2.plot(G_eff_trace, "r--", lw=2, label="G_eff")
ax2.plot(hbar_eff_trace, "g--", lw=2, label="ħ_eff")
ax.set_title("G5 - Energy, Entropy, and Effective (G, ħ)")
ax.set_xlabel("step")
ax.set_ylabel("⟨L⟩ / entropy")
ax2.set_ylabel("effective constants")
lns = ax.get_lines() + ax2.get_lines()
labs = [l.get_label() for l in lns]
ax.legend(lns, labs, loc="upper right")
plt.tight_layout()
plt.savefig("PAEV_TestG5_Unification_Trace.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG5_Unification_Trace.png")

# 2) Λ proxy vs time
plt.figure(figsize=(7.5, 3.6))
plt.plot(Lambda_proxy_trace, lw=2, color="black")
plt.axhline(0.0, color="gray", ls="--", lw=1)
plt.title("G5 - Λ proxy = K - I (qualitative consistency with G1)")
plt.xlabel("step")
plt.ylabel("Λ_proxy (arb.)")
plt.tight_layout()
plt.savefig("PAEV_TestG5_LambdaProxy.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG5_LambdaProxy.png")

# 3) Phase portrait: I vs K (with iso-ρ_P lines)
I_arr = np.array(I_trace)
K_arr = np.array([alpha_K * safe_mean(kappa**2 + delta_curv*grad2_kappa) for _ in range(1)])  # dummy to keep style
K_arr = np.array([alpha_K * safe_mean(kappa**2 + delta_curv*grad2_kappa) for _ in I_trace])   # recompute length
rho_arr = I_arr * K_arr
plt.figure(figsize=(6.0, 5.4))
plt.plot(I_arr, K_arr, color="orange", lw=2)
rp = np.median(rho_arr)
xs = np.linspace(max(I_arr.min(), 1e-6), max(I_arr.max(), 1e-6)*1.05, 200)
plt.plot(xs, rp/np.clip(xs, 1e-9, None), "k--", lw=1.5, label="iso-ρ_P (median)")
plt.xlabel("Information density I")
plt.ylabel("Curvature density K")
plt.title("G5 - Phase Portrait: I vs K")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestG5_PhasePortrait_IK.png", dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestG5_PhasePortrait_IK.png")

# 4) Animation (sanity)
if frames:
    imageio.mimsave("PAEV_TestG5_Unification_Fields.gif", frames, fps=10)
    print("✅ Saved animation to: PAEV_TestG5_Unification_Fields.gif")

# ----------------------------
# summary text
# ----------------------------
E_final = E_trace[-1]
S_final = S_trace[-1]
G_final = G_eff_trace[-1]
h_final = hbar_eff_trace[-1]
Lam_final = Lambda_proxy_trace[-1]

summary = f"""
=== Test G5 - Planck-Scale Unification Calibration ===
Final diagnostics (dimensionless, normalized units):
  ⟨L⟩ final            = {E_final:.6e}
  Spectral entropy S    = {S_final:.6f}
  G_eff (final)         = {G_final:.6e}
  ħ_eff (final)         = {h_final:.6e}
  Λ_proxy (final = K-I) = {Lam_final:.6e}

Heuristic mappings:
  ρ_P  ~ I * K
  G_eff ~ 1 / sqrt(ρ_P)
  ħ_eff ~ sqrt(I / (K + ε))

Files:
  - PAEV_TestG5_Unification_Trace.png
  - PAEV_TestG5_LambdaProxy.png
  - PAEV_TestG5_PhasePortrait_IK.png
  - PAEV_TestG5_Unification_Fields.gif
"""

with open("PAEV_TestG5_Summary.txt", "w", encoding="utf-8") as f:
    f.write(summary)
print("✅ Saved file: PAEV_TestG5_Summary.txt")

print("\n=== Test G5 - Planck-Scale Unification Calibration Complete ===")
print(f"⟨L⟩ final = {E_final:.6e}")
print(f"S (final) = {S_final:.6f}")
print(f"G_eff     = {G_final:.6e}")
print(f"ħ_eff     = {h_final:.6e}")
print(f"Λ_proxy   = {Lam_final:.6e}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")