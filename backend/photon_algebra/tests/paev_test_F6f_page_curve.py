# ==========================================================
# Test F6f - Page Curve & Information Recovery Simulation
# ----------------------------------------------------------
# Purpose:
#   Track inside/outside entanglement-entropy proxies during
#   horizon evaporation and show a Page-like curve.
#
# Outputs:
#   - Page curve: S_inside(t), S_outside(t), S_total(t)
#   - Info flux: dS_outside/dt vs dS_inside/dt
#   - Energy/area traces
#   - Field animation (ψ, κ)
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# Numerics & helpers
# ----------------------------
def laplacian(Z):
    return (-4.0 * Z
            + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
            + np.roll(Z, 1, 1) + np.roll(Z, -1, 1))

def grad2(Z):
    gx = 0.5 * (np.roll(Z, -1, 1) - np.roll(Z, 1, 1))
    gy = 0.5 * (np.roll(Z, -1, 0) - np.roll(Z, 1, 0))
    return gx*gx + gy*gy

def shannon_entropy(p):
    # safe Shannon entropy for nonnegative p summing to 1
    p = np.clip(p, 1e-16, 1.0)
    return float(-np.sum(p * np.log(p)))

def region_entropy_proxy(psi2, mask):
    """Von Neumann proxy from normalized |psi|^2 within region."""
    w = psi2[mask]
    Z = float(np.sum(w)) + 1e-16
    p = (w / Z).ravel()
    return shannon_entropy(p)

# ----------------------------
# Grid & initial fields
# ----------------------------
N = 96
x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)
R = np.sqrt(X**2 + Y**2)

# Complex field ψ and curvature κ
rng = np.random.default_rng(7)
psi = 0.1 * (rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N)))
psi_t = np.zeros_like(psi, dtype=complex)

# Initial "black hole" curvature well (horizon ~ radius r_h0)
r_h0 = 0.45
kappa = 0.6 * np.exp(-((R / r_h0)**2))
kappa += 0.01 * rng.standard_normal((N, N))  # small roughness

# ----------------------------
# Dynamics parameters (gentle/stable)
# ----------------------------
dt = 0.02
steps = 600
c1 = 0.35      # wave coupling for ψ
chi = 0.10     # ψ-κ coupling
gamma = 0.02   # damping for ψ
eta = 0.04     # κ relaxation
alpha = 0.015  # κ evaporation rate baseline
flux_gain = 0.05  # feedback of flux onto evaporation
eps = 1e-12

# Evaporation control via horizon radius shrink
r_h = r_h0

# Traces
S_in_trace, S_out_trace, S_tot_trace = [], [], []
E_trace, A_trace, flux_trace = [], [], []
frames = []

# Masks update function
def masks_from_radius(r):
    inside = R <= r
    outside = ~inside
    return inside, outside

inside_mask, outside_mask = masks_from_radius(r_h)

# ----------------------------
# Main loop
# ----------------------------
for t in range(steps):
    # --- ψ dynamics (complex Klein-Gordon-like with curvature coupling) ---
    lap_re = laplacian(psi.real)
    lap_im = laplacian(psi.imag)
    lap_psi = lap_re + 1j * lap_im

    # curvature-coupled term: div(kappa ∇ψ) ≈ ∇*(κ∇ψ)
    gx_re = 0.5 * (np.roll(psi.real, -1, 1) - np.roll(psi.real, 1, 1))
    gy_re = 0.5 * (np.roll(psi.real, -1, 0) - np.roll(psi.real, 1, 0))
    gx_im = 0.5 * (np.roll(psi.imag, -1, 1) - np.roll(psi.imag, 1, 1))
    gy_im = 0.5 * (np.roll(psi.imag, -1, 0) - np.roll(psi.imag, 1, 0))

    div_k_grad_re = (np.roll(kappa*gx_re, -1, 1) - np.roll(kappa*gx_re, 1, 1)) * 0.5 \
                  + (np.roll(kappa*gy_re, -1, 0) - np.roll(kappa*gy_re, 1, 0)) * 0.5
    div_k_grad_im = (np.roll(kappa*gx_im, -1, 1) - np.roll(kappa*gx_im, 1, 1)) * 0.5 \
                  + (np.roll(kappa*gy_im, -1, 0) - np.roll(kappa*gy_im, 1, 0)) * 0.5
    div_k_grad = div_k_grad_re + 1j * div_k_grad_im

    psi_tt = c1 * lap_psi + chi * div_k_grad - gamma * psi_t
    psi_t  = psi_t + dt * psi_tt
    psi    = psi   + dt * psi_t

    # --- κ dynamics + evaporation (Hawking-like) ---
    # flux proxy from gradient energy near the horizon shell
    shell = np.logical_and(R > (r_h*0.95), R < (r_h*1.05))
    grad_energy = float(np.mean(grad2(psi.real)[shell] + grad2(psi.imag)[shell])) if np.any(shell) else 0.0

    # local evaporation rate: α + flux feedback
    evap = alpha + flux_gain * grad_energy
    kappa = kappa + dt * (eta * laplacian(kappa) - evap * kappa)

    # shrink horizon radius proportional to flux (softly)
    r_h = max(0.12, r_h - 0.03 * dt * (1.0 + 40.0 * grad_energy))
    inside_mask, outside_mask = masks_from_radius(r_h)

    # --- Observables ---
    psi2 = (psi.real**2 + psi.imag**2)
    # energy proxy (kinetic + gradient + κ^2)
    E = float(np.mean(np.abs(psi_t)**2 + 0.5*grad2(psi.real) + 0.5*grad2(psi.imag) + 0.01*kappa**2))
    # horizon "area" = number of inside pixels (∝ area)
    A = int(np.sum(inside_mask))

    # entropies
    S_in  = region_entropy_proxy(psi2, inside_mask)
    S_out = region_entropy_proxy(psi2, outside_mask)
    # global probability
    Ztot = float(np.sum(psi2)) + eps
    p_all = (psi2 / Ztot).ravel()
    S_tot = shannon_entropy(p_all)

    # flux trace (use gradient energy in shell as proxy)
    flux = grad_energy

    # store
    S_in_trace.append(S_in)
    S_out_trace.append(S_out)
    S_tot_trace.append(S_tot)
    E_trace.append(E)
    A_trace.append(A)
    flux_trace.append(flux)

    # make animation frame every 12 steps
    if t % 12 == 0:
        # normalize visuals robustly
        def norm_img(Z):
            zmin, zmax = float(np.nanpercentile(Z, 1)), float(np.nanpercentile(Z, 99))
            Zc = np.clip((Z - zmin) / (max(zmax - zmin, 1e-9)), 0, 1)
            return np.uint8(plt.cm.plasma(Zc) * 255)

        tile_top = np.concatenate([
            norm_img(psi.real), norm_img(psi.imag)
        ], axis=1)
        tile_bot = np.concatenate([
            norm_img(kappa), norm_img(psi2)
        ], axis=1)
        frame = np.concatenate([tile_top, tile_bot], axis=0)
        frames.append(frame)

# ----------------------------
# Plots
# ----------------------------
# Page curve
plt.figure(figsize=(7.2, 4.4))
plt.plot(S_in_trace, label="S_inside (Page)")
plt.plot(S_out_trace, label="S_outside")
plt.plot(S_tot_trace, label="S_total", alpha=0.7)
plt.xlabel("Time step")
plt.ylabel("Entropy (proxy)")
plt.title("Test F6f - Page Curve & Information Recovery")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestF6f_PageCurve.png", dpi=150)
plt.close()
print("✅ Saved file: PAEV_TestF6f_PageCurve.png")

# Info flux (derivatives)
S_in_dt  = np.gradient(np.array(S_in_trace))
S_out_dt = np.gradient(np.array(S_out_trace))
plt.figure(figsize=(7.2, 4.2))
plt.plot(S_in_dt, label="dS_inside/dt")
plt.plot(S_out_dt, label="dS_outside/dt")
plt.plot(flux_trace, label="Flux (shell, proxy)", alpha=0.7)
plt.xlabel("Time step")
plt.ylabel("Rate / Flux (arb.)")
plt.title("Test F6f - Information Flux vs. Evaporation")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestF6f_InfoFlux.png", dpi=150)
plt.close()
print("✅ Saved file: PAEV_TestF6f_InfoFlux.png")

# Energy & area traces
plt.figure(figsize=(7.2, 4.2))
plt.plot(E_trace, label="Energy proxy ⟨E⟩")
plt.plot(A_trace, label="Area (pixels)")
plt.xlabel("Time step")
plt.ylabel("Value")
plt.title("Test F6f - Energy & Horizon Area")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestF6f_EnergyArea.png", dpi=150)
plt.close()
print("✅ Saved file: PAEV_TestF6f_EnergyArea.png")

# Animation
imageio.mimsave("PAEV_TestF6f_Propagation.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestF6f_Propagation.gif")

# ----------------------------
# Console summary
# ----------------------------
# Find rough Page time: argmax of S_inside
page_step = int(np.argmax(np.array(S_in_trace)))
print("\n=== Test F6f - Page Curve & Information Recovery Complete ===")
print(f"Page time (argmax S_inside): step {page_step}")
print(f"S_inside(final) = {S_in_trace[-1]:.3f}")
print(f"S_outside(final)= {S_out_trace[-1]:.3f}")
print(f"S_total(final)  = {S_tot_trace[-1]:.3f}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")