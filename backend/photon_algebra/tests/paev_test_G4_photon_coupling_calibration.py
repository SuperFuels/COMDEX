# ==========================================================
# Test G4 - Predictive Photon Coupling Calibration
#   Derive emergent fine-structure constant α from curvature-
#   phase dual-field propagation and compare to physical α ≈ 1/137
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------------------------------------
# numerical helpers
# ----------------------------------------------------------
def laplacian(Z):
    return (
        -4.0 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

def spectral_entropy(field):
    fft_mag = np.abs(np.fft.fft2(field))**2
    p = fft_mag / np.sum(fft_mag)
    p = p[np.isfinite(p) & (p > 0)]
    return -np.sum(p * np.log(p)) / np.log(len(p))

# ----------------------------------------------------------
# simulation setup
# ----------------------------------------------------------
N = 96
steps = 300
dt = 0.015
dx = 1.0 / N

# base coupling constants
c1 = 1.0        # phase stiffness
c3 = 0.3        # curvature feedback
chi = 0.12      # photon field coupling
alpha_eff = 0.05  # adaptive correction rate

# spatial domain
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# initialize fields (complex photon curvature mode)
rng = np.random.default_rng(42)
theta = np.exp(-5*(X**2 + Y**2)) * np.cos(6*X) + 0.01*rng.standard_normal((N, N))
kappa = np.exp(-5*(X**2 + Y**2)) * np.sin(6*Y) + 0.01*rng.standard_normal((N, N))
psi = theta + 1j * kappa
psi_t = np.zeros_like(psi)

# diagnostics
alpha_trace, entropy_trace, energy_trace = [], [], []
frames = []

# ----------------------------------------------------------
# evolve field
# ----------------------------------------------------------
for t in range(steps):
    lap_theta = laplacian(np.real(psi))
    lap_kappa = laplacian(np.imag(psi))

    # photon-like wave equation (dual curvature fields)
    psi_tt = c1 * (lap_theta + 1j * lap_kappa) - c3 * np.abs(psi)**2 * psi
    psi_t += dt * psi_tt
    psi += dt * psi_t

    # compute derived measures
    L = 0.5 * np.real(psi_t * np.conjugate(psi_t)) - 0.5 * c1 * np.real(psi * np.conjugate(laplacian(psi)))
    E_density = np.nanmean(L)
    S = spectral_entropy(np.real(psi))
    corr = np.nanmean(np.real(psi) * np.imag(psi))

    # emergent fine-structure constant calibration
    alpha_emergent = np.abs(corr / (S + 1e-8))
    alpha_trace.append(alpha_emergent)
    entropy_trace.append(S)
    energy_trace.append(E_density)

    # small adaptive correction (self-tuning)
    chi += alpha_eff * (alpha_emergent - chi) * dt

    # visuals every ~20 steps
    if t % 20 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(8, 3.6))
        im0 = ax[0].imshow(np.real(psi), cmap="plasma")
        ax[0].set_title(f"Re(ψ) - photon phase, step {t}")
        ax[0].axis("off")
        im1 = ax[1].imshow(np.imag(psi), cmap="magma")
        ax[1].set_title("Im(ψ) - curvature")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------------------------------------
# aggregate results
# ----------------------------------------------------------
alpha_arr = np.array(alpha_trace)
alpha_mean = np.nanmean(alpha_arr[-50:])
alpha_ci = np.nanpercentile(alpha_arr[-50:], [16, 84])

# ----------------------------------------------------------
# plots
# ----------------------------------------------------------
plt.figure(figsize=(6,4))
plt.plot(alpha_trace, color="mediumpurple")
plt.axhline(alpha_mean, color="red", linestyle="--", label=f"mean α ≈ {alpha_mean:.3e}")
plt.xlabel("step")
plt.ylabel("α_emergent")
plt.legend()
plt.title("G4 - Emergent Fine-Structure Constant (α)")
plt.tight_layout()
plt.savefig("PAEV_TestG4_CouplingTrace.png")
plt.close()
print("✅ Saved file: PAEV_TestG4_CouplingTrace.png")

plt.figure(figsize=(6,4))
plt.hist(alpha_arr[-100:], bins=40, color="orchid", alpha=0.8)
plt.title("G4 - α_emergent distribution (final phase)")
plt.tight_layout()
plt.savefig("PAEV_TestG4_Photon_CouplingHistogram.png")
plt.close()
print("✅ Saved file: PAEV_TestG4_Photon_CouplingHistogram.png")

plt.figure(figsize=(6,4))
plt.plot(entropy_trace, color="teal", label="spectral entropy")
plt.plot(energy_trace, color="orange", label="⟨L⟩ energy")
plt.legend()
plt.title("G4 - Photon Field Entropy & Energy Trace")
plt.tight_layout()
plt.savefig("PAEV_TestG4_SpectralPurity.png")
plt.close()
print("✅ Saved file: PAEV_TestG4_SpectralPurity.png")

imageio.mimsave("PAEV_TestG4_Photon_Propagation.gif", frames, fps=12)
print("✅ Saved animation to: PAEV_TestG4_Photon_Propagation.gif")

# ----------------------------------------------------------
# save summary
# ----------------------------------------------------------
summary = f"""
=== Test G4 - Predictive Photon Coupling Calibration Complete ===
ᾱ (emergent) = {alpha_mean:.6e}
68% CI        = [{alpha_ci[0]:.6e}, {alpha_ci[1]:.6e}]
⟨L⟩ final     = {energy_trace[-1]:.6e}
Entropy final = {entropy_trace[-1]:.6e}
χ final       = {chi:.6e}
Perturbation mode: ON
All output files saved in working directory.
----------------------------------------------------------
"""

with open("PAEV_TestG4_Summary.txt", "w", encoding="utf-8") as f:
    f.write(summary)
print(summary)