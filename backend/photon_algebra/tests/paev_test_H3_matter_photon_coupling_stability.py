# PAEV Test H3 — Matter–Photon Coupling Stability
# Stable hybrid of scalar "matter" field φ, photon/quantum field ψ, and curvature κ
# Saves: traces, entropy, and final-field snapshots, then prints their paths.

import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)

# ----------------------------
# Grid & integration settings
# ----------------------------
N = 128
steps = 600
dt = 0.01
x = np.linspace(-1, 1, N, endpoint=False)
X, Y = np.meshgrid(x, x, indexing="ij")

# ----------------------------
# Fields: ψ (complex), φ (real), κ (real)
# ----------------------------
psi = 0.05 * (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) * np.exp(
    -((X**2 + Y**2) / 0.5)
)
phi = 0.9 + 0.05 * rng.normal(size=(N, N))  # “mass/Higgs-like” scalar near vev
kappa = 0.02 * np.exp(-((X**2 + Y**2) / 0.4)) + 0.002 * rng.normal(size=(N, N))

psi = psi.astype(np.complex128)
phi = phi.astype(np.float64)
kappa = kappa.astype(np.float64)

# ----------------------------
# Utilities
# ----------------------------
def laplacian(Z):
    # periodic 5-point stencil
    return (
        -4.0 * Z
        + np.roll(Z, 1, 0)
        + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1)
        + np.roll(Z, -1, 1)
    )

def spectral_entropy(field):
    """Robust, normalized spectral entropy of |FFT(field)|^2."""
    F = np.fft.fft2(field)
    P = np.abs(F) ** 2
    total = np.sum(P)
    if not np.isfinite(total) or total <= 0:
        return 0.0
    p = P / total
    # prevent log(0)
    p = np.clip(p, 1e-16, None)
    S = -np.sum(p * np.log(p))
    # normalize by log of number of modes
    return float(S / np.log(p.size))

def grad2(Z):
    gx = (np.roll(Z, -1, 1) - np.roll(Z, 1, 1)) * 0.5
    gy = (np.roll(Z, -1, 0) - np.roll(Z, 1, 0)) * 0.5
    return gx**2 + gy**2

# ----------------------------
# Couplings / coefficients (tuned for stability)
# ----------------------------
# ψ evolution (Schrödinger-like with curvature & φ coupling)
gamma_rel = 0.9           # mild relativistic factor
g_phi = 0.25              # ψ–φ coupling
g_kappa = 0.25            # ψ–κ coupling
nu_damp = 0.01            # small damping for stability

# φ evolution (Ginzburg–Landau-like)
D_phi = 0.15
lam = 0.20                # self-coupling (quartic)
v = 1.0                   # vacuum expectation value
beta_psi = 0.08           # sourcing from |ψ|^2
gamma_phi = 0.03          # relaxation

# κ evolution (diffusive curvature with sources)
D_k = 0.10
alpha_psi = 0.05
eta_phi = 0.04
gamma_k = 0.03

# Value clamps to prevent numerical blowups
def clamp_inplace(A, lo, hi):
    np.clip(A, lo, hi, out=A)

# ----------------------------
# Logs
# ----------------------------
E_trace = []
C_trace = []  # < |ψ| * κ >
S_trace = []

# ----------------------------
# Time stepping
# ----------------------------
for t in range(steps):
    # --- ψ update (complex)
    lap_psi = laplacian(psi)
    psi_rhs = (1j) * (lap_psi - g_phi * phi * psi - g_kappa * kappa * psi)
    psi += dt * (gamma_rel * psi_rhs - nu_damp * psi)

    # small noise to avoid stuck states (very tiny)
    psi += (1e-5) * (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N)))

    # --- φ update (real)
    lap_phi = laplacian(phi)
    Vprime = lam * (phi**3 - (v**2) * phi)  # d/dφ [ (lam/4) (φ^2 - v^2)^2 ]
    phi += dt * (D_phi * lap_phi - Vprime + beta_psi * np.abs(psi) ** 2 - gamma_phi * phi)

    # --- κ update (real)
    lap_k = laplacian(kappa)
    kappa += dt * (D_k * lap_k + alpha_psi * np.abs(psi) ** 2 + eta_phi * (phi - v) - gamma_k * kappa)

    # --- safety clamps
    clamp_inplace(phi, -3.0, 3.0)
    clamp_inplace(kappa, -0.5, 0.5)
    psi_real = np.real(psi)
    psi_imag = np.imag(psi)
    clamp_inplace(psi_real, -3.0, 3.0)
    clamp_inplace(psi_imag, -3.0, 3.0)
    psi = psi_real + 1j * psi_imag

    # --- diagnostics
    E_proxy = np.mean(grad2(np.real(psi)) + grad2(np.imag(psi))) \
              + 0.5 * lam * np.mean((phi**2 - v**2) ** 2) \
              + 0.5 * np.mean(kappa**2)

    coupling = np.mean(np.abs(psi) * kappa)
    S = spectral_entropy(np.abs(psi))

    E_trace.append(E_proxy)
    C_trace.append(coupling)
    S_trace.append(S)

    if t % 120 == 0 or t == steps - 1:
        print(f"Step {t:03d} — ⟨E⟩={E_proxy:.4e}, ⟨|ψ|·κ⟩={coupling:.4e}, S={S:.4f}")

# ----------------------------
# Save figures
# ----------------------------
trace_path = "PAEV_TestH3_EnergyCoupling.png"
entropy_path = "PAEV_TestH3_SpectralEntropy.png"
fields_path = "PAEV_TestH3_FinalFields.png"

plt.figure(figsize=(7, 4))
plt.plot(E_trace, label="Energy ⟨E⟩")
plt.plot(C_trace, label="Coupling ⟨|ψ|·κ⟩")
plt.title("H3 — Energy & Coupling Stability")
plt.xlabel("step")
plt.legend()
plt.tight_layout()
plt.savefig(trace_path, dpi=160)
plt.close()

plt.figure(figsize=(7, 4))
plt.plot(S_trace, color="purple")
plt.title("H3 — Spectral Entropy (|ψ|)")
plt.xlabel("step")
plt.ylabel("entropy (normalized)")
plt.tight_layout()
plt.savefig(entropy_path, dpi=160)
plt.close()

fig, axs = plt.subplots(1, 3, figsize=(12, 4))
im0 = axs[0].imshow(np.real(psi), cmap="magma")
axs[0].set_title("Re(ψ) — final")
plt.colorbar(im0, ax=axs[0], fraction=0.046, pad=0.04)

im1 = axs[1].imshow(phi, cmap="viridis")
axs[1].set_title("φ — final")
plt.colorbar(im1, ax=axs[1], fraction=0.046, pad=0.04)

im2 = axs[2].imshow(kappa, cmap="inferno")
axs[2].set_title("κ — final")
plt.colorbar(im2, ax=axs[2], fraction=0.046, pad=0.04)

plt.tight_layout()
plt.savefig(fields_path, dpi=160)
plt.close()

print("\n=== Test H3 — Matter–Photon Coupling Stability Complete ===")
print(f"⟨E⟩ final          = {E_trace[-1]:.6e}")
print(f"⟨|ψ|·κ⟩ final      = {C_trace[-1]:.6e}")
print(f"Spectral Entropy   = {S_trace[-1]:.6f}")
print("All output files saved:")
print(f" - {trace_path}")
print(f" - {entropy_path}")
print(f" - {fields_path}")
print("----------------------------------------------------------")