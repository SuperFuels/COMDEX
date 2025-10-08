#!/usr/bin/env python3
# ==========================================================
# G10b–RC5 — Scale-Invariant Energy–Entropy Law
# Detects diffusive (p ≈ 1/2) or general scale-invariant behavior
# across grid scales using integrated energy–entropy curves.
# ==========================================================

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path
from backend.photon_algebra.utils.load_constants import load_constants

# ---------------- Load constants ----------------
const = load_constants()
ħ = const.get("ħ", 1.0e-3)
G = const.get("G", 1.0e-5)
Λ = const.get("Λ", 1.0e-6)
α = const.get("α", 0.5)
β = const.get("β", 0.2)
c = const.get("c", 2.99792458e8)
kB = const.get("kB", 1.380649e-23)

# ---------------- Source metadata ----------------
src_meta = Path("backend/modules/knowledge/G10RC3_multiscale.json")
if not src_meta.exists():
    raise FileNotFoundError("❌ Run paev_test_G10_multiscale.py first (produces G10RC3_multiscale.json).")
with open(src_meta) as f:
    base = json.load(f)
scales = sorted(int(k) for k in base["per_scale"].keys())

# ---------------- Simulation parameters ----------------
steps = 600
L = 6.0
D_psi, D_kappa = 0.3, 0.02
gamma_psi, gamma_kappa = 0.02, 0.01
coupling, source = 0.05, 0.01
damping, amp_limit = 0.994, 2.5


def evolve_integrated(N):
    """Evolve ψ–κ system and compute integrated energy vs. entropy."""
    x = np.linspace(-L / 2, L / 2, N)
    dx = x[1] - x[0]
    dt = 0.18 * (dx**2 / max(D_psi, D_kappa))  # CFL-stable

    psi = np.exp(-x**2 * 6.0) * (1.0 + 0.08j)
    kappa = 0.20 * np.exp(-x**2 * 3.0)
    S_vals, E_int_vals = [], []
    E_cum = 0.0

    for _ in range(steps):
        lap_psi = (np.roll(psi, -1) + np.roll(psi, 1) - 2 * psi) / dx**2
        lap_k = (np.roll(kappa, -1) + np.roll(kappa, 1) - 2 * kappa) / dx**2

        psi_t = D_psi * lap_psi - gamma_psi * psi + 1j * coupling * kappa * psi
        k_t = D_kappa * lap_k - gamma_kappa * kappa + source * np.abs(psi)**2

        psi = damping * (psi + dt * psi_t)
        kappa = damping * (kappa + dt * k_t)
        psi = np.clip(psi.real, -amp_limit, amp_limit) + 1j * np.clip(psi.imag, -amp_limit, amp_limit)

        # Shannon entropy of |ψ|²
        prob = np.abs(psi)**2
        p = prob / (np.trapezoid(prob, x) + 1e-12)
        S = float(np.trapezoid(-p * np.log(p + 1e-12), x))

        # Energy proxy and integration
        grad_psi = (np.roll(psi, -1) - psi) / dx
        E = float(np.trapezoid(np.abs(grad_psi)**2 + 0.5 * np.abs(kappa)**2, x))
        E_cum += E * dt

        S_vals.append(S)
        E_int_vals.append(E_cum)

    S = np.array(S_vals)
    E_int = np.array(E_int_vals)
    S = (S - S.min()) / (S.max() - S.min() + 1e-12)
    E_int = (E_int - E_int.min()) / (E_int.max() - E_int.min() + 1e-12)
    return S, E_int


# ---------------- Run for all scales ----------------
SE = {N: evolve_integrated(N) for N in scales}

# ---------------- Fit log–log scaling ----------------
fits = {}
for N, (S, E) in SE.items():
    mask = (S > 1e-4) & (E > 1e-6)
    if np.sum(mask) < 10:
        continue
    logS, logE = np.log(S[mask]), np.log(E[mask])
    p, b = np.polyfit(logS, logE, 1)
    yhat = p * logS + b
    r2 = 1 - np.sum((logE - yhat) ** 2) / (np.sum((logE - np.mean(logE)) ** 2) + 1e-12)
    fits[N] = {"p": float(p), "k": float(np.exp(b)), "R2": float(r2)}

p_arr = np.array([v["p"] for v in fits.values()])
p_mean, p_std = float(np.mean(p_arr)), float(np.std(p_arr))


# ---------------- Cross-scale curve collapse ----------------
def collapse_deviation(SE_dict):
    Sgrid = np.logspace(-3, -0.05, 140)
    curves = []
    for N, (S, E) in SE_dict.items():
        mask = (S > 1e-4) & (E > 1e-6)
        if np.sum(mask) < 5:
            continue
        idx = np.argsort(S[mask])
        S_m, E_m = S[mask][idx], E[mask][idx]
        curves.append(np.exp(np.interp(np.log(Sgrid), np.log(S_m + 1e-18), np.log(E_m + 1e-18))))
    if len(curves) < 2:
        return float("nan")
    C = np.vstack(curves)
    return float(np.sqrt(np.mean((C - C.mean(axis=0)) ** 2)))


collapse_dev = collapse_deviation(SE)


# ---------------- Classification ----------------
if p_std < 0.02 and collapse_dev < 0.02:
    if abs(p_mean - 0.5) < 0.05:
        verdict = "✅ Scale-invariant law detected (diffusive class: p≈1/2)."
    else:
        verdict = f"✅ Scale-invariant law detected (p≈{p_mean:.2f})."
elif p_std < 0.05 and collapse_dev < 0.06:
    verdict = "⚠️ Near-universal (minor drift)."
else:
    verdict = "❌ Non-universal scaling (exponent varies across scales)."


# ---------------- Plot: Energy–Entropy curves ----------------
plt.figure(figsize=(8, 5))
for N, (S, E) in SE.items():
    mask = (S > 1e-4) & (E > 1e-6)
    plt.loglog(S[mask], E[mask], label=f"N={N}")
    if N in fits:
        p = fits[N]["p"]
        plt.text(S[mask][-1] * 0.9, E[mask][-1] * 0.9, f"p={p:.2f}")
plt.title("G10b–RC5 — Integrated Energy–Entropy Scaling Across Scales")
plt.xlabel("Entropy S (normalized)")
plt.ylabel("Integrated Energy E_int (normalized)")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_G10bRC5_IntegratedScaling.png", dpi=150)

# ---------------- Plot: Exponent by scale ----------------
plt.figure(figsize=(7, 4))
Ns = list(fits.keys())
ps = [fits[n]["p"] for n in Ns]
plt.plot(Ns, ps, "o-", lw=1.2)
plt.axhline(0.5, ls="--", alpha=0.6, label="diffusive fixed point (p=0.5)")
plt.title("G10b–RC5 — Fitted Exponent p vs. Scale")
plt.xlabel("Grid size N")
plt.ylabel("Exponent p")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_G10bRC5_ExponentByScale.png", dpi=150)


# ---------------- Save results ----------------
out = {
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β, "c": c, "kB": kB},
    "parameters": {
        "scales": scales,
        "steps": steps,
        "L": L,
        "D_psi": D_psi,
        "D_kappa": D_kappa,
        "gamma_psi": gamma_psi,
        "gamma_kappa": gamma_kappa,
        "coupling": coupling,
        "source": source,
        "damping": damping,
        "amp_limit": amp_limit,
    },
    "metrics": {
        "fits": fits,
        "p_mean": p_mean,
        "p_std": p_std,
        "collapse_deviation": collapse_dev,
    },
    "classification": verdict,
    "files": {
        "scaling_plot": "FAEV_G10bRC5_IntegratedScaling.png",
        "exponent_plot": "FAEV_G10bRC5_ExponentByScale.png",
        "input_source": str(src_meta),
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}

out_path = "backend/modules/knowledge/G10bRC5_energy_entropy_universality.json"
with open(out_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== G10b–RC5 — Scale-Invariant Energy–Entropy Law ===")
print(f"p_mean={p_mean:.3f} | p_std={p_std:.3f} | collapse_dev={collapse_dev:.4f}")
print(f"→ {verdict}")
print(f"✅ Results saved → {out_path}")