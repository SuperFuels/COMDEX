# -*- coding: utf-8 -*-
"""
F16 - Quantum Gravity & the Multiverse (entangled wormhole network)
-------------------------------------------------------------------
Goal:
  Simulate a multiverse built from an entangled wormhole network (M1/F14),
  and test whether the emergent effective cosmological constant Λ_eff varies
  across domains.

Method (toy-but-consistent with F14/F13b style):
  * Build a κ(x) "landscape" with multiple curvature wells (wormhole throats).
  * Spawn D semi-independent domains by sampling different wells + couplings.
  * Evolve per-domain proxies:
        - entropy S_d(t)
        - curvature energy E_d(t)
        - mutual-information rate Ī_d(t)
    then compute a smoothed Λ_eff,d(t) via feedback:
        Λ̇ = β [ E' - S' ] + ξ Ī - ζ (Λ - Λ_eq)
  * Measure diversity of terminal Λ_eff across domains.

Outputs:
  * PAEV_F16_LambdaDiversity.png
  * PAEV_F16_SampleTraces.png
  * PAEV_F16_LandscapeMap.png
  * backend/modules/knowledge/F16_quantum_gravity_multiverse.json
"""
from __future__ import annotations
import json, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

# -----------------------------
# constants (fallback registry)
# -----------------------------
CANDIDATES = [
    Path("backend/modules/knowledge/constants_v1.2.json"),
    Path("backend/modules/knowledge/constants_v1.1.json"),
    Path("backend/modules/knowledge/constants_v1.0.json"),
]
for p in CANDIDATES:
    if p.exists():
        constants = json.loads(p.read_text())
        break
else:
    constants = {}
ħ   = float(constants.get("ħ", 1e-3))
G   = float(constants.get("G", 1e-5))
α   = float(constants.get("α", 0.5))
Λ0  = float(constants.get("Λ", 1e-6))

# -----------------------------
# simulation knobs
# -----------------------------
SEED        = 42
rng         = np.random.default_rng(SEED)
D           = 48
W           = 9
Lx, Ly      = 12.0, 12.0
well_spread = 0.9

T, dt       = 2400, 0.006
t           = np.arange(T) * dt

β           = 0.020
ξ           = 0.015
ζ           = 0.060
Λ_eq        = Λ0
τ_div       = 0.25

# -----------------------------
# landscape generation
# -----------------------------
def make_wells(W, Lx, Ly, spread, rng):
    centers = rng.uniform([-Lx/2, -Ly/2], [Lx/2, Ly/2], size=(W, 2))
    depths  = rng.lognormal(mean=np.log(1.0), sigma=0.35, size=W) * spread
    widths  = rng.uniform(0.8, 1.6, size=W)
    return {"centers": centers, "depths": depths, "widths": widths}

land = make_wells(W, Lx, Ly, well_spread, rng)

def sample_domain_params(land, rng):
    i = rng.integers(0, len(land["depths"]))
    depth, width, center = land["depths"][i], land["widths"][i], land["centers"][i]
    I_dot_amp = max(0.05, 0.5 + 1.2*depth + 0.15*rng.standard_normal())
    βd = β * (1.0 + 0.15*rng.standard_normal())
    ξd = ξ * (1.0 + 0.15*rng.standard_normal())
    ζd = ζ * (1.0 + 0.10*rng.standard_normal())
    return dict(well_index=i, center=center, depth=depth, width=width,
                beta=βd, xi=ξd, zeta=ζd, I_amp=I_dot_amp)

domains = [sample_domain_params(land, rng) for _ in range(D)]

# -----------------------------
# per-domain evolution
# -----------------------------
def ema(prev, x, a=0.03): return (1-a)*prev + a*x if prev is not None else x

def evolve_domain(par, t, rng):
    φs, φe, φi = rng.uniform(0, 2*np.pi, size=3)
    S  = 0.70 + 0.06*np.sin(0.16*t + 0.4 + φs) + 0.01*rng.standard_normal(len(t))
    E  = 0.10*np.sin(0.48*t + φe) + 0.05*np.cos(0.22*t + 0.7) + 0.01*rng.standard_normal(len(t))
    İ  = par["I_amp"]*(0.45 + 0.55*np.sin(0.21*t + φi))

    S_sm_prev = E_sm_prev = None
    dS, dE = np.zeros_like(t), np.zeros_like(t)
    for k in range(1, len(t)):
        S_sm = ema(S_sm_prev, S[k], a=0.04); S_sm_prev = S_sm
        E_sm = ema(E_sm_prev, E[k], a=0.04); E_sm_prev = E_sm
        dS[k], dE[k] = (S_sm - S[k-1]), (E_sm - E[k-1])

    Λ = np.zeros_like(t); Λ[0] = Λ_eq
    for k in range(1, len(t)):
        Λ_dot = par["beta"]*(dE[k] - dS[k]) + par["xi"]*max(İ[k], 0.0) - par["zeta"]*(Λ[k-1] - Λ_eq)
        Λ[k]  = Λ[k-1] + dt*Λ_dot

    return {"S": S, "E": E, "Irate": İ, "Lambda": Λ}

evo = [evolve_domain(par, t, rng) for par in domains]

# -----------------------------
# analysis
# -----------------------------
Λ_final = np.array([ev["Lambda"][-1] for ev in evo])
Λ_mean, Λ_min, Λ_max, Λ_std = map(float, [np.mean(Λ_final), np.min(Λ_final), np.max(Λ_final), np.std(Λ_final)])
rel_range = float((Λ_max - Λ_min) / (abs(Λ_mean) + 1e-12))
classification = ("✅ Multiverse-like Λ diversity" if rel_range >= τ_div else "⚠️ Homogeneous Λ across domains")

print("=== F16 - Quantum Gravity & Multiverse Test ===")
print(f"ħ={ħ:.1e}, α={α:.2f}, Λ0={Λ0:.2e}, β={β:.3f}, ξ={ξ:.3f}, ζ={ζ:.3f}")
print(f"D={D}, W={W} -> Λ_mean={Λ_mean:.6f}, spread={rel_range:.3f}")
print(f"-> {classification}")

# -----------------------------
# visualization
# -----------------------------
out = Path(".")

# Λ diversity histogram
plt.figure(figsize=(8,4))
plt.hist(Λ_final, bins=12, alpha=0.75, color="royalblue", edgecolor="black", density=True)
plt.axvline(Λ_mean, color="red", linestyle="--", label="Λ_mean")
plt.title("F16 - Λ_eff Diversity Across Domains")
plt.xlabel("Λ_eff (final)"); plt.ylabel("Density"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_F16_LambdaDiversity.png", dpi=160)

# Sample traces
plt.figure(figsize=(9,4))
for idx in rng.choice(range(D), size=6, replace=False):
    plt.plot(t, evo[idx]["Lambda"], lw=1.3, alpha=0.8)
plt.title("F16 - Representative Λ_eff(t) Traces")
plt.xlabel("time"); plt.ylabel("Λ_eff(t)"); plt.tight_layout()
plt.savefig(out/"PAEV_F16_SampleTraces.png", dpi=160)

# Landscape map
plt.figure(figsize=(6,6))
for i, (cx, cy) in enumerate(land["centers"]):
    plt.scatter(cx, cy, s=300*land["depths"][i], alpha=0.3, color="gray")
for d, par in enumerate(domains):
    x, y = par["center"]
    plt.scatter(x + 0.2*rng.standard_normal(), y + 0.2*rng.standard_normal(),
                s=40, color="royalblue", alpha=0.8)
plt.title("F16 - κ-Well Landscape & Domain Distribution")
plt.xlabel("x"); plt.ylabel("y"); plt.tight_layout()
plt.savefig(out/"PAEV_F16_LandscapeMap.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_F16_LambdaDiversity.png")
print("  - PAEV_F16_SampleTraces.png")
print("  - PAEV_F16_LandscapeMap.png")

# -----------------------------
# save knowledge summary
# -----------------------------
summary = {
    "ħ": ħ, "G": G, "α": α, "Λ0": Λ0,
    "β": β, "ξ": ξ, "ζ": ζ, "Λ_eq": Λ_eq,
    "domains": D, "wells": W,
    "timing": {"steps": T, "dt": dt},
    "metrics": {
        "Λ_mean": Λ_mean,
        "Λ_min": Λ_min,
        "Λ_max": Λ_max,
        "Λ_std": Λ_std,
        "rel_range": rel_range,
    },
    "classification": classification,
    "files": {
        "lambda_diversity_plot": "PAEV_F16_LambdaDiversity.png",
        "sample_traces_plot": "PAEV_F16_SampleTraces.png",
        "landscape_plot": "PAEV_F16_LandscapeMap.png",
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
out_path = Path("backend/modules/knowledge/F16_quantum_gravity_multiverse.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved -> {out_path}")