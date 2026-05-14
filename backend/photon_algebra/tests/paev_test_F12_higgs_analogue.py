#!/usr/bin/env python3
"""
PAEV Test F12 - Higgs Analogue & Collider Smash
Run: PYTHONPATH=. python backend/photon_algebra/tests/paev_test_F12_higgs_analogue.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from matplotlib import cm

# -------------------------
# Config / knobs (change these to stress-test)
# -------------------------
OUT_DIR = "."
N = 128                # spatial grid
steps = 600            # time steps
dt = 0.005             # time step (small for stability)
save_every = 6
vis_every = 6

# Higgs-analogue params
lambda_h = 0.12        # self-coupling (quartic)
v = 1.0                # vacuum expectation value
chi = 0.25             # curvature↔phi coupling (increase to stress)
damping_phi = 0.005    # viscous damping on phi
damping_kappa = 0.01   # damping on curvature

# "Collider" / soliton smash params
do_smash = True
smash_step = 80
soliton_amp = 1.6      # increase to do 'more damage'
soliton_sigma = 0.08   # width in normalized coords

# Numerical safeguards
CLIP_ABS = 1e6         # clip large values to avoid overflow
EPS = 1e-12

# -------------------------
# Helpers
# -------------------------
def laplacian(Z):
    return (
        -4.0 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

def spectral_entropy(field):
    # power in Fourier domain, safe
    fft = np.fft.fft2(field)
    mag2 = np.abs(fft)**2
    s = np.sum(mag2)
    if s <= 0:
        return 0.0
    p = mag2.flatten() / (s + EPS)
    # small cutoff to avoid log(0)
    p = np.where(p > 0, p, 1e-30)
    H = -np.sum(p * np.log(p)) / np.log(len(p))
    return float(H)

def gaussian_centered(N, X, Y, x0, y0, sigma):
    return np.exp(-((X - x0)**2 + (Y - y0)**2) / (2.0 * sigma**2))

# -------------------------
# Grid setup
# -------------------------
x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)

# initial fields: phi near vacuum (v), small noise
rng = np.random.default_rng(43)
phi = v + 0.05 * rng.standard_normal((N, N))
phi_t = np.zeros_like(phi)

# curvature field kappa localized lens (can be zero if you prefer)
kappa = 0.08 * np.exp(-((X**2 + Y**2) / 0.25)) + 0.01 * rng.standard_normal((N, N))
kappa_t = np.zeros_like(kappa)

# Storage
energy_trace = []
phi_mean_trace = []
phi_entropy_trace = []
kappa_mean_trace = []
mass_est_trace = []
frames = []

# Collision helper (two solitons moving towards center)
def add_solitons(phi, amp, sigma, t):
    # place two Gaussians from +/- x positions moving inward
    # here we add instantaneous perturbation at smash_step for simplicity
    g1 = amp * gaussian_centered(N, X, Y, -0.5, 0.0, sigma)
    g2 = amp * gaussian_centered(N, X, Y,  0.5, 0.0, sigma)
    return phi + g1 + g2

# -------------------------
# Main loop
# -------------------------
print("💥 Running F12 - Higgs analogue collider-smash. Knock it up with soliton_amp or chi to 'do damage'.")
for t in range(steps):
    # laplacians
    lap_phi = laplacian(phi)
    lap_kappa = laplacian(kappa)

    # potential derivative (dV/dphi = lambda*(phi^3 - v^2 * phi))
    Vp = lambda_h * (phi**3 - v**2 * phi)

    # equation of motion (wave-like) with coupling to curvature
    phi_tt = lap_phi - Vp + chi * kappa * phi - damping_phi * phi_t
    # integrate (velocity Verlet-ish simple)
    phi_t = phi_t + dt * phi_tt
    phi = phi + dt * phi_t

    # kappa evolution (relax + driven by phi gradients)
    gpx, gpy = np.gradient(phi)
    grad2 = gpx**2 + gpy**2
    kappa_tt = 0.03 * lap_kappa + 0.05 * (grad2 - np.mean(grad2)) - damping_kappa * kappa_t
    kappa_t = kappa_t + dt * kappa_tt
    kappa = kappa + dt * kappa_t

    # clamp / sanitize to avoid catastrophic overflow
    if not np.isfinite(phi).all() or np.nanmax(np.abs(phi)) > CLIP_ABS:
        phi = np.clip(phi, -CLIP_ABS, CLIP_ABS)
        phi_t = np.clip(phi_t, -CLIP_ABS, CLIP_ABS)
    if not np.isfinite(kappa).all() or np.nanmax(np.abs(kappa)) > CLIP_ABS:
        kappa = np.clip(kappa, -CLIP_ABS, CLIP_ABS)
        kappa_t = np.clip(kappa_t, -CLIP_ABS, CLIP_ABS)

    # hammer it: collision (single-time perturbation)
    if do_smash and t == smash_step:
        phi = add_solitons(phi, soliton_amp, soliton_sigma, t)
        print(f"⨁ Smash injected at step {t} (amp={soliton_amp})")

    # diagnostics
    grad2_phi = (np.gradient(phi)[0]**2 + np.gradient(phi)[1]**2)
    energy = np.nanmean(0.5 * (phi_t**2 + grad2_phi) + 0.25 * lambda_h * (phi**2 - v**2)**2)
    energy_trace.append(float(energy))
    phi_mean_trace.append(float(np.nanmean(phi)))
    kappa_mean_trace.append(float(np.nanmean(kappa)))

    # effective "mass" estimate: look at dominant frequency of phi at center (rough proxy)
    center_signal = phi[N//2 - 2:N//2 + 3, N//2 - 2:N//2 + 3].ravel()
    mass_est = np.nanstd(center_signal)
    mass_est_trace.append(float(mass_est))

    # spectral entropy every step (costly but N small)
    phi_entropy_trace.append(spectral_entropy(phi))

    # frame for animation occasionally
    if t % vis_every == 0:
        fig, ax = plt.subplots(1, 2, figsize=(7.5, 3.5))
        im = ax[0].imshow(phi, cmap="twilight", vmin=-1.5*v, vmax=1.5*v)
        ax[0].set_title(f"φ @ step {t}")
        ax[0].axis("off")
        im2 = ax[1].imshow(kappa, cmap="magma")
        ax[1].set_title("κ curvature")
        ax[1].axis("off")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# -------------------------
# Post-run plots + animations
# -------------------------
os.makedirs(OUT_DIR, exist_ok=True)

# energy + entropy traces
plt.figure(figsize=(8,4))
plt.plot(energy_trace, label="<E> (phi energy)")
plt.plot(np.array(phi_entropy_trace) * np.max(energy_trace), label="spectral entropy (scaled)", alpha=0.9)
plt.xlabel("step")
plt.legend()
plt.title("F12 - Higgs analogue: energy & entropy")
fn = os.path.join(OUT_DIR, "PAEV_TestF12_Higgs_EnergyEntropy.png")
plt.savefig(fn, dpi=160, bbox_inches="tight")
plt.close()
print("✅ Saved file:", fn)

# phi mean + kappa mean + mass proxy
plt.figure(figsize=(8,4))
plt.subplot(1,2,1)
plt.plot(phi_mean_trace, label="<phi>")
plt.plot(kappa_mean_trace, label="<kappa>")
plt.xlabel("step")
plt.legend()
plt.title("Field means")
plt.subplot(1,2,2)
plt.plot(mass_est_trace, label="mass_proxy (std center)")
plt.xlabel("step")
plt.legend()
plt.title("Mass-like proxy")
fn = os.path.join(OUT_DIR, "PAEV_TestF12_Higgs_Traces.png")
plt.savefig(fn, dpi=160, bbox_inches="tight")
plt.close()
print("✅ Saved file:", fn)

# spectral power (final)
phi_fft = np.fft.fftshift(np.abs(np.fft.fft2(phi))**2)
phi_fft_log = np.log10(phi_fft + 1e-30)
plt.figure(figsize=(5,5))
plt.imshow(phi_fft_log, origin='lower', cmap='magma')
plt.colorbar(label='log10 |phi(k)|^2')
plt.title("F12 - φ Field Spectrum (final)")
fn = os.path.join(OUT_DIR, "PAEV_TestF12_Higgs_Spectrum.png")
plt.savefig(fn, dpi=160, bbox_inches="tight")
plt.close()
print("✅ Saved file:", fn)

# animation
if frames:
    gif_fn = os.path.join(OUT_DIR, "PAEV_TestF12_Higgs_Propagation.gif")
    imageio.mimsave(gif_fn, frames, fps=12)
    print("✅ Saved animation to:", gif_fn)

# textual summary
summary = f"""
=== Test F12 - Higgs Analogue Collider-smash ===
Parameters:
  lambda_h = {lambda_h:.3g}, v = {v:.3g}, chi = {chi:.3g}
  soliton_amp = {soliton_amp:.3g}, smash_step = {smash_step}
Results (final):
  <E> final = {energy_trace[-1]:.6e}
  <phi> final = {phi_mean_trace[-1]:.6e}
  <kappa> final = {kappa_mean_trace[-1]:.6e}
  spectral entropy (final) = {phi_entropy_trace[-1]:.6e}
  mass proxy (final) = {mass_est_trace[-1]:.6e}
All output files saved in working directory.
"""
with open(os.path.join(OUT_DIR, "PAEV_TestF12_Higgs_Summary.txt"), "w") as f:
    f.write(summary)
print(summary)