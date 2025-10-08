#!/usr/bin/env python3
# ==========================================================
# G10-RC3 — Multiscale Invariance (CFL-stable + auto-renorm)
# Runs ψ–κ evolution on three grids and checks Page-curve collapse.
# Captures plots + JSON registry with constants & metrics.
# ==========================================================

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from backend.photon_algebra.utils.load_constants import load_constants

# --------------------------
# Unified constants (loader)
# --------------------------
const = load_constants()
ħ = const.get("ħ", 1.0e-3)
G = const.get("G", 1.0e-5)
Λ = const.get("Λ", 1.0e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
c = const.get("c", 2.99792458e8)
kB = const.get("kB", 1.380649e-23)

# --------------------------
# Test parameters
# --------------------------
scales = [96, 128, 192]
L = 6.0
steps = 600                   # a bit longer so t* is well-defined
D_psi, D_kappa = 0.30, 0.02   # baseline Laplacian coeffs
gamma_psi, gamma_k = 0.020, 0.010
couple = 0.050                # ψ–κ coupling strength at reference grid (N=128)
source_k = 0.010              # |ψ|^2 → κ source @ reference grid
damping = 0.994               # global envelope damping
amp_limit = 2.5               # soft clipping to avoid blowups
rng = np.random.default_rng(42)

# CFL base: dt_ref matches N=128 and D~max(D_psi, D_kappa)
dx_ref = L / 128.0
dt_ref = 0.18 * dx_ref**2 / max(D_psi, D_kappa)   # conservative CFL (explicit)

# --------------------------
# Helpers
# --------------------------
def soft_clip(z, limit):
    mag = np.abs(z)
    mask = mag > limit
    if np.any(mask):
        z = z.copy()
        z[mask] *= (limit / (mag[mask] + 1e-12))
    return z

def entropy_shannon(prob, x):
    # S = -∫ p log p dx  (p normalized)
    p = prob / (np.trapz(prob, x) + 1e-12)
    return float(np.trapz(-p * np.log(p + 1e-12), x))

def evolve_one_scale(N):
    """
    Returns:
      t: array of times
      S: entropy curve (Shannon of |ψ|^2)
      E: simple energy proxy curve
      Smax, t_star: peak entropy and time of peak
    """
    x = np.linspace(-L/2, L/2, N)
    dx = x[1] - x[0]
    # CFL-safe dt
    dt = dt_ref * (dx / dx_ref)**2

    # scale-by-grid renormalization:
    # - Laplacian already has 1/dx^2. Keep D fixed.
    # - Interaction terms scale with local volume/gradient scales ~ dx (1D).
    #   Empirically we get best collapse if we scale ψ–κ couplings as (dx/dx_ref)
    #   and the |ψ|^2 source the same way.
    scale_int = (dx / dx_ref)

    # initial conditions (same physical shape in x)
    psi = np.exp(-x**2 * 6.0) * (1.0 + 0.08j)
    kappa = 0.20 * np.exp(-x**2 * 3.0)
    psi *= 1.0 + 0.02 * rng.standard_normal(psi.shape)
    kappa *= 1.0 + 0.02 * rng.standard_normal(kappa.shape)

    S, E = [], []
    t = np.zeros(steps)

    for i in range(steps):
        # Laplacians
        lap_psi = (np.roll(psi, -1) + np.roll(psi, 1) - 2.0 * psi) / dx**2
        lap_k = (np.roll(kappa, -1) + np.roll(kappa, 1) - 2.0 * kappa) / dx**2

        # Explicit updates (damped)
        psi_t = (D_psi * lap_psi
                 - gamma_psi * psi
                 + 1j * (couple * scale_int) * kappa * psi)
        k_t = (D_kappa * lap_k
               - gamma_k * kappa
               + (source_k * scale_int) * (np.abs(psi)**2))

        psi = damping * (psi + dt * psi_t)
        kappa = damping * (kappa + dt * k_t)

        # soft amplitude guard (prevents overflow cascades)
        psi = soft_clip(psi, amp_limit)
        kappa = soft_clip(kappa, amp_limit)

        # observables
        prob = np.abs(psi)**2
        S.append(entropy_shannon(prob, x))

        grad_psi = (np.roll(psi, -1) - psi) / dx
        E_proxy = np.trapz(np.abs(grad_psi)**2 + 0.5*np.abs(kappa)**2, x)
        E.append(float(E_proxy))

        t[i] = (i+1) * dt

    S = np.array(S)
    E = np.array(E)

    # Page-like normalization point t* = argmax S
    i_star = int(np.argmax(S))
    Smax = float(S[i_star])
    t_star = float(t[i_star]) if i_star > 0 else float(t[-1])

    return t, S, E, Smax, t_star, dt

# --------------------------
# Run all scales
# --------------------------
curves = {}  # N -> dict
for N in scales:
    t, S, E, Smax, t_star, dt_eff = evolve_one_scale(N)
    curves[N] = {
        "t": t, "S": S, "E": E,
        "Smax": Smax, "t_star": t_star, "dt": dt_eff
    }

# --------------------------
# Collapse & metrics
# --------------------------
# Interpolate each curve to a common normalized time grid 0..1
u = np.linspace(0.0, 1.0, 200)

def norm_curve(S, Smax, t, t_star):
    # Normalize time by t*, and entropy by Seq (= Smax) so Page-like curves line up.
    if t_star <= 0 or Smax == 0:
        return np.full_like(u, np.nan)
    tau = np.clip(t / t_star, 0, 1.0)
    # normalized entropy S/Smax as function of tau
    return np.interp(u, tau, S / (Smax + 1e-12))

normed = {}
for N, d in curves.items():
    normed[N] = norm_curve(d["S"], d["Smax"], d["t"], d["t_star"])

# Collapse deviation = average L2 distance of each curve from the mean curve
stack = np.vstack([normed[N] for N in scales])
mean_curve = np.nanmean(stack, axis=0)
dev = 0.0
valid_count = 0
for row in stack:
    if np.any(np.isnan(row)): 
        continue
    dev += float(np.sqrt(np.mean((row - mean_curve)**2)))
    valid_count += 1
collapse_dev = dev / max(valid_count, 1)

# Classification
if np.isnan(collapse_dev) or not np.isfinite(collapse_dev):
    verdict = "❌ Invalid metric (numerical instability)"
elif collapse_dev < 0.05:
    verdict = "✅ Multiscale collapse (universal within tolerance)"
elif collapse_dev < 0.20:
    verdict = "⚠️ Near-universal (minor scale drift)"
else:
    verdict = "❌ Scale Dependence Detected (needs renorm tuning)"

# --------------------------
# Plots
# --------------------------
# 1) Raw entropy
plt.figure(figsize=(9, 5))
for N in scales:
    plt.plot(curves[N]["S"], label=f"N={N}", lw=1.4)
plt.title("G10-RC3 — Raw Entropy Evolution (CFL-stable)")
plt.xlabel("Step"); plt.ylabel("Entropy (Shannon of |ψ|²)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G10RC3_EntropyEvolution.png", dpi=150)

# 2) Page-curve collapse
plt.figure(figsize=(9, 5))
for N in scales:
    plt.plot(u, normed[N], label=f"N={N}", lw=1.4)
plt.title("G10-RC3 — Multiscale Page Curve Collapse (Normalized)")
plt.xlabel("Normalized time t/t*"); plt.ylabel("S/Smax")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G10RC3_PageCollapse.png", dpi=150)

# 3) Energy–Entropy scaling (each scale normalized by its own max)
plt.figure(figsize=(9, 5))
for N in scales:
    S = curves[N]["S"]; E = curves[N]["E"]
    S_n = (S - S.min()) / (S.max() - S.min() + 1e-12)
    E_n = (E - E.min()) / (E.max() - E.min() + 1e-12)
    plt.plot(S_n, E_n, label=f"N={N}", lw=1.2)
plt.title("G10-RC3 — Energy–Entropy Scaling Across Scales")
plt.xlabel("Normalized Entropy"); plt.ylabel("Normalized Energy")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G10RC3_EnergyEntropy.png", dpi=150)

# --------------------------
# Save JSON registry
# --------------------------
results = {
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "c": c, "kB": kB
    },
    "parameters": {
        "scales": scales, "steps": steps, "L": L,
        "D_psi": D_psi, "D_kappa": D_kappa,
        "gamma_psi": gamma_psi, "gamma_kappa": gamma_k,
        "coupling_ref": couple, "source_ref": source_k,
        "damping": damping, "amp_limit": amp_limit,
        "dt_ref": dt_ref
    },
    "renormalization": {
        "method": "CFL-stable dt ~ dx^2; ψ–κ couplings ~ (dx/dx_ref)",
        "dx_ref": dx_ref,
        "notes": "Keeps diffusion physics invariant across N; rescales local interactions by physical cell size."
    },
    "per_scale": {
        str(N): {
            "dt": curves[N]["dt"],
            "Smax": curves[N]["Smax"],
            "t_star": curves[N]["t_star"]
        } for N in scales
    },
    "metrics": {
        "collapse_deviation": collapse_dev
    },
    "classification": verdict,
    "files": {
        "entropy_plot": "FAEV_G10RC3_EntropyEvolution.png",
        "collapse_plot": "FAEV_G10RC3_PageCollapse.png",
        "energy_entropy_plot": "FAEV_G10RC3_EnergyEntropy.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

out_path = "backend/modules/knowledge/G10RC3_multiscale.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

print("=== G10-RC3 — Multiscale Invariance (CFL + auto-renorm) ===")
print(f"collapse_deviation={collapse_dev:.6f}")
print(f"→ {verdict}")
print(f"✅ Results saved → {out_path}")