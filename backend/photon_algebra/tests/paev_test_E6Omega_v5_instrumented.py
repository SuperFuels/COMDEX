#!/usr/bin/env python3
"""
PAEV — E6-Ω v5 (Instrumented)
Entanglement proxy + v_S instrumentation + adaptive variance controller

This test evolves a two-channel Tessaris-like field, computes an entanglement
proxy (CHSH-like S) from binary sign measurements at four analyzer settings,
and *simultaneously* measures the entropic front velocity v_S relative to
the causal speed v_c = sqrt(alpha / Lambda).

It logs a time series of (t, v_S, v_S/v_c, S_CHSH) to:
  backend/modules/knowledge/E6Omega_vS_trace.json

and produces a scatter/trace figure:
  PAEV_E6Omega_vS_vs_CHSH.png

NOTE (important):
- This is a *model-based* entanglement proxy inside the Tessaris algebra. It is
  designed for *internal discovery correlation* with I3/I4, not as a claim
  about physical-spacetime superluminal signaling.
"""

import json
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

print("=== E6-Ω v5 — Instrumented Entanglement + v_S ===")

# ──────────────────────────────────────────────────────────────────────────────
# Constants loader (compatible with v1.0–v1.2 knowledge registry)
# ──────────────────────────────────────────────────────────────────────────────
CANDIDATES = [
    Path("backend/modules/knowledge/constants_v1.2.json"),
    Path("backend/modules/knowledge/constants_v1.1.json"),
    Path("backend/modules/knowledge/constants_v1.0.json"),
]

for p in CANDIDATES:
    if p.exists():
        CREG = json.loads(p.read_text())
        break
else:
    CREG = {"constants": {"ħ": 1e-3, "G": 1e-5, "Λ": 1e-6, "α": 0.5, "β": 0.2}}

def get_const(d, *names, default=None):
    for n in names:
        if n in d:
            return d[n]
    return default

C = CREG.get("constants", CREG)  # allow flat or nested
ħ = get_const(C, "ħ", "hbar", "h", default=1e-3)
G = get_const(C, "G", "grav", default=1e-5)
Λ = get_const(C, "Λ", "Lambda", "lambda", default=1e-6)
α = get_const(C, "α", "alpha", default=0.5)
β = get_const(C, "β", "beta", default=0.2)

# ──────────────────────────────────────────────────────────────────────────────
# Parameters
# ──────────────────────────────────────────────────────────────────────────────
params = dict(
    N=256,
    T=4000,
    dt=0.01,
    base_noise=0.012,
    kappa_var_start=0.02,         # starting curvature variance
    kappa_var_max=0.25,           # hard cap for safety
    controller=dict(
        enabled=True,
        theta=1.7,                # threshold on v_S/v_c to amplify variance
        eta_up=0.20,              # +20% on exceed
        eta_dn=0.05               # -5% decay otherwise
    ),
    chsh_angles=dict(
        a=0.0,
        a_p=np.pi/4,
        b=np.pi/8,
        b_p=3*np.pi/8
    ),
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers: initialization, evolution, entropy/MSD, CHSH proxy
# ──────────────────────────────────────────────────────────────────────────────
rng = np.random.default_rng(1759930045)

def initialize_pair(N, var_k):
    # Two channels (phi_A, phi_B) share a latent correlated component
    latent = rng.normal(0, np.sqrt(var_k), N)
    noiseA = rng.normal(0, 1, N)
    noiseB = rng.normal(0, 1, N)
    phi_A = latent + 0.5 * noiseA
    phi_B = latent + 0.5 * noiseB
    return phi_A, phi_B

def laplacian_1d(x):
    return np.roll(x, -1) - 2.0*x + np.roll(x, 1)

def step_pair(phi_A, phi_B, dt, alpha, Lambda, noise_amp, kappa_var):
    # Simple coupled nonlinear diffusion with curvature-like modulation
    lapA = laplacian_1d(phi_A)
    lapB = laplacian_1d(phi_B)
    kappa = rng.normal(0, np.sqrt(kappa_var), phi_A.shape[0])

    # weak symmetric coupling via kappa gradient surrogate
    phi_A = phi_A + dt*(alpha*(lapA + 0.2*kappa*lapB) - Lambda*phi_A - G*phi_A**3) \
                    + noise_amp * rng.normal(0, 1, phi_A.shape[0])
    phi_B = phi_B + dt*(alpha*(lapB + 0.2*kappa*lapA) - Lambda*phi_B - G*phi_B**3) \
                    + noise_amp * rng.normal(0, 1, phi_B.shape[0])
    return phi_A, phi_B

def entropy_of_frame(frame, bins=64):
    hist, _ = np.histogram(np.abs(frame), bins=bins, density=True)
    hist = hist[hist > 0]
    if hist.size == 0:
        return 0.0
    return float(-np.sum(hist * np.log(hist)))

def compute_measurement(bitstream, theta):
    """
    Binary outcomes (+1/-1) projected along analyzer angle theta.
    Here we create a simple phase-sensitive projection using a sinusoidal kernel.
    """
    N = bitstream.size
    x = np.arange(N)
    kernel = np.cos(2*np.pi*(x/N) + theta)
    proj = np.sign(np.dot(bitstream, kernel))
    return 1 if proj >= 0 else -1

def chsh_proxy(phi_A, phi_B, angles):
    """
    Build a CHSH S estimate using sign-correlation at four angle pairs.
    This is a *proxy* metric inside the algebra (not a physical Bell test).
    """
    a, a_p, b, b_p = angles["a"], angles["a_p"], angles["b"], angles["b_p"]
    # Reduce each field to ±1 outcomes under the analyzer setting
    A_a   = compute_measurement(np.sign(phi_A), a)
    A_ap  = compute_measurement(np.sign(phi_A), a_p)
    B_b   = compute_measurement(np.sign(phi_B), b)
    B_bp  = compute_measurement(np.sign(phi_B), b_p)

    # Empirical "expectations" from single-shot proxy (±1)
    E_ab   = A_a  * B_b
    E_abp  = A_a  * B_bp
    E_apb  = A_ap * B_b
    E_apbp = A_ap * B_bp

    S = E_ab - E_abp + E_apb + E_apbp
    # Smooth a bit by mixing in norm-based coherence (optional, bounded)
    coh = np.tanh(0.1*(np.mean(np.abs(phi_A)) + np.mean(np.abs(phi_B))))
    S = float(S + 0.5*coh)
    # Keep within a sensible numeric window
    return float(np.clip(S, -3.0, 3.0))

# ──────────────────────────────────────────────────────────────────────────────
# Run loop with instrumentation and controller
# ──────────────────────────────────────────────────────────────────────────────
N, T, dt = params["N"], params["T"], params["dt"]
noise = params["base_noise"]
kappa_var = params["kappa_var_start"]
angles = params["chsh_angles"]
ctrl = params["controller"]

phi_A, phi_B = initialize_pair(N, kappa_var)

# For v_S = (dS/dt)/(dD/dt) we track entropy S(t) and MSD(t)
def MSD(a, b):  # use both channels' mean for displacement proxy
    return float(np.mean((a - a.mean())**2 + (b - b.mean())**2))

S_prev = entropy_of_frame(phi_A) + entropy_of_frame(phi_B)
D_prev = MSD(phi_A, phi_B)
v_c = float(np.sqrt(α / Λ))

records = []
S_vals = []
for t in range(1, T+1):
    # evolve one step
    phi_A, phi_B = step_pair(phi_A, phi_B, dt, α, Λ, noise, kappa_var)

    # entropy & displacement
    S_now = entropy_of_frame(phi_A) + entropy_of_frame(phi_B)
    D_now = MSD(phi_A, phi_B)

    dS_dt = (S_now - S_prev) / dt
    dD_dt = (D_now - D_prev) / dt
    v_s   = dS_dt / (dD_dt + 1e-12)

    # CHSH-like proxy (use current fields)
    S_chsh = chsh_proxy(phi_A, phi_B, angles)

    # record
    records.append({
        "t": float(t*dt),
        "v_s": float(v_s),
        "v_s_over_v_c": float(v_s / (v_c + 1e-12)),
        "S_CHSH": float(S_chsh),
        "kappa_var": float(kappa_var)
    })
    S_vals.append(S_chsh)

    # controller (if enabled)
    if ctrl["enabled"]:
        if (v_s / (v_c + 1e-12)) > ctrl["theta"]:
            kappa_var *= (1.0 + ctrl["eta_up"])
        else:
            kappa_var *= (1.0 - ctrl["eta_dn"])
        # keep bounded
        kappa_var = float(np.clip(kappa_var, 1e-4, params["kappa_var_max"]))

    S_prev, D_prev = S_now, D_now

# ──────────────────────────────────────────────────────────────────────────────
# Outputs: JSON + figure
# ──────────────────────────────────────────────────────────────────────────────
out_json = {
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "params": params,
    "results": {
        "v_c": v_c,
        "S_CHSH_stats": {
            "mean": float(np.mean(S_vals)),
            "max": float(np.max(S_vals)),
            "min": float(np.min(S_vals))
        },
        "discovery_notes": [
            "Model-level correlation test between v_S bursts and CHSH-like S.",
            "All claims pertain to Tessaris algebra; no spacetime signaling is implied."
        ]
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}
trace_path = Path("backend/modules/knowledge/E6Omega_vS_trace.json")
trace_path.write_text(json.dumps({"records": records, **out_json}, indent=2))

# scatter + running mean
vs = np.array([r["v_s_over_v_c"] for r in records])
Sx = np.array([r["S_CHSH"] for r in records])

plt.figure(figsize=(7,5))
plt.scatter(vs, Sx, s=6, alpha=0.35)
# running mean (simple box)
if vs.size > 50:
    idx = np.argsort(vs)
    vs_sorted = vs[idx]
    S_sorted = Sx[idx]
    w = max(10, vs.size//50)
    run = np.convolve(S_sorted, np.ones(w)/w, mode="valid")
    v_mid = np.convolve(vs_sorted, np.ones(w)/w, mode="valid")
    plt.plot(v_mid, run, linewidth=2.0)

plt.xlabel("v_S / v_c")
plt.ylabel("S_CHSH (proxy)")
plt.title("E6-Ω v5 — v_S bursts vs entanglement proxy (model)")
plt.tight_layout()
fig_path = "PAEV_E6Omega_vS_vs_CHSH.png"
plt.savefig(fig_path, dpi=200)

summary_path = Path("backend/modules/knowledge/E6Omega_v5_summary.json")
summary = dict(out_json)
summary["files"] = {"scatter": fig_path, "trace": str(trace_path)}
summary_path.write_text(json.dumps(summary, indent=2))

print(json.dumps(summary, indent=2))
print(f"✅ Trace saved → {trace_path}")
print(f"✅ Summary saved → {summary_path}")
print(f"✅ Figure saved → {fig_path}")