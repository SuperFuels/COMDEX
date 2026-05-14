"""
A1c - Stabilized Anti-Gravity / Negative-Energy Bubble
------------------------------------------------------
Goal:
    Refined version of A1b introducing nonlinear negative-pressure coupling
    and PI-style feedback to sustain NEC<0 regions with negative entropy flow.

Upgrades:
    * Adds -χ|ψ|2ψ nonlinear term (negative-pressure proxy)
    * Gaussian-weighted bubble instead of hard mask
    * PI controller on entropy slope for stronger feedback
    * Clamped α, Λ actuators for stability
    * Boosted gradient weight in NEC proxy (pressure emphasis)

Outputs:
    * PAEV_A1c_NEC_TimeSeries.png
    * PAEV_A1c_EntropySlope.png
    * PAEV_A1c_BubbleProfile.png
    * PAEV_A1c_NEC_Histogram.png
    * backend/modules/knowledge/A1c_antigravity_bubble.json
"""

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# -------------------------
# 1) Constants
# -------------------------
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

ħ = float(constants.get("ħ", 1e-3))
G = float(constants.get("G", 1e-5))
Λ0 = float(constants.get("Λ", 1e-6))
α0 = float(constants.get("α", 0.5))
β  = float(constants.get("β", 0.2))
np.random.seed(42)

# -------------------------
# 2) Grid setup
# -------------------------
N, L = 512, 50.0
dx = L / N
x = np.linspace(-L/2, L/2, N)

# Gaussian bubble gain
sigma_b = 2.5
bubble_gain = np.exp(-(x**2)/(2*sigma_b**2))

psi = np.exp(-(x/6.0)**2) * np.exp(1j*0.4*x) * (1.0 + 0.01*np.random.randn(N))
psi = psi.astype(np.complex128)
psi_t = np.zeros_like(psi)

def laplacian_1d(z):
    return (np.roll(z, -1) - 2*z + np.roll(z, 1)) / (dx**2)

# -------------------------
# 3) Parameters
# -------------------------
T_steps = 6000
dt = 0.001

# Controller parameters
k_alpha, k_lambda = 8e-3, 4e-3
k_i = 5e-3
i_accum = 0.0
alpha = α0 * np.ones(N)
Lambda = Λ0 * np.ones(N)

# Nonlinear negative-pressure coefficient
chi = 0.6

# Data traces
S_trace, dSdt_trace = [], []
NEC_trace, NEC_min_trace = [], []
alpha_center_trace, Lambda_center_trace = [], []

def ema(prev, val, alpha=0.02):
    return (1-alpha)*prev + alpha*val if prev is not None else val

S_prev_sm = None

# -------------------------
# 4) Time evolution loop
# -------------------------
for t in range(T_steps):
    lap = laplacian_1d(psi)

    # Nonlinear negative-pressure coupling
    nonlinear = -chi * np.abs(psi)**2 * psi

    psi_tt = 1j*ħ*lap - alpha*psi + 1j*Lambda*psi + nonlinear
    psi_t += dt*psi_tt
    psi   += dt*psi_t

    # Entropy proxy
    amp2 = np.abs(psi)**2 + 1e-12
    S = -np.mean(amp2 * np.log(amp2))
    S_trace.append(S)

    # Smoothed dS/dt
    if len(S_trace) > 1:
        dS = S_trace[-1] - S_trace[-2]
        dSdt_sm = ema(S_prev_sm, dS/dt, alpha=0.05)
        S_prev_sm = dSdt_sm
        dSdt_trace.append(dSdt_sm)
    else:
        dSdt_trace.append(0.0)

    # NEC proxy
    grad_psi = (np.roll(psi, -1) - np.roll(psi, 1)) / (2*dx)
    rho = ħ * np.real(psi_t * np.conj(psi))
    p   = 1.2 * np.abs(grad_psi)**2          # pressure weighted
    NEC = rho + p

    NEC_center = np.mean(NEC[bubble_gain > 0.1])
    NEC_trace.append(NEC_center)
    NEC_min_trace.append(np.min(NEC[bubble_gain > 0.1]))

    # --- PI feedback on entropy slope ---
    dSdt_local = np.mean(dSdt_trace[-10:]) if len(dSdt_trace) >= 10 else dSdt_trace[-1]
    i_accum = 0.995 * i_accum + dSdt_local
    drive = dSdt_local + k_i * i_accum

    alpha  = np.clip(α0 - k_alpha  * drive * bubble_gain,  0.05,  1.2)
    Lambda = np.clip(Λ0 - k_lambda * drive * bubble_gain, -0.03,  0.03)

    alpha_center_trace.append(alpha[N//2])
    Lambda_center_trace.append(Lambda[N//2])

# -------------------------
# 5) Diagnostics
# -------------------------
NEC_time_mean = float(np.mean(NEC_trace))
NEC_time_min  = float(np.min(NEC_min_trace))
frac_exotic   = float(np.mean(np.array(NEC_min_trace) < 0.0))
dSdt_tail_mean = float(np.mean(dSdt_trace[-max(50, T_steps//20):]))

if (frac_exotic >= 0.55 and NEC_time_min <= -5e-4 and dSdt_tail_mean < 0):
    classification = "✅ Stable Exotic Bubble (NEC<0 sustained, entropy reversed)"
elif (frac_exotic >= 0.15 and NEC_time_min < -1e-4):
    classification = "⚠️ Transient Exotic Phase"
else:
    classification = "❌ No Exotic Phase"

print("=== A1c - Stabilized Anti-Gravity / Negative-Energy Bubble ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ0={Λ0:.3e}, α0={α0:.3f}, χ={chi:.2f}")
print(f"⟨NEC⟩_bubble = {NEC_time_mean:.3e} | min_t NEC = {NEC_time_min:.3e}")
print(f"fraction(NEC<0) = {frac_exotic:.2f} | tail ⟨dS/dt⟩ = {dSdt_tail_mean:.3e}")
print(f"-> {classification}")

# -------------------------
# 6) Plots
# -------------------------
out_dir = Path(".")
plt.figure(figsize=(9,4.5))
plt.plot(NEC_trace, lw=1.2, label="⟨NEC⟩ in bubble")
plt.plot(NEC_min_trace, lw=1.0, alpha=0.7, label="min(NEC) in bubble")
plt.axhline(0.0, color="k", ls="--", lw=0.8)
plt.title("A1c - NEC Proxy in Bubble (ρ + p)")
plt.xlabel("time step"); plt.ylabel("NEC proxy")
plt.legend(); plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1c_NEC_TimeSeries.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(dSdt_trace, lw=1.2)
plt.axhline(0.0, color="k", ls="--", lw=0.8)
plt.title("A1c - Entropy Slope dS/dt (EMA)")
plt.xlabel("time step"); plt.ylabel("dS/dt")
plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1c_EntropySlope.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(alpha_center_trace, label="α(center)")
plt.plot(Lambda_center_trace, label="Λ(center)")
plt.title("A1c - Bubble Control Profiles at Center")
plt.xlabel("time step"); plt.ylabel("value")
plt.legend(); plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1c_BubbleProfile.png", dpi=160)

plt.figure(figsize=(6,4))
plt.hist(NEC_min_trace, bins=60, color="slateblue", alpha=0.75)
plt.axvline(0, color="k", lw=1, ls="--")
plt.title("A1c - Distribution of min(NEC) in Bubble")
plt.xlabel("NEC value"); plt.ylabel("frequency")
plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1c_NEC_Histogram.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_A1c_NEC_TimeSeries.png")
print("  - PAEV_A1c_EntropySlope.png")
print("  - PAEV_A1c_BubbleProfile.png")
print("  - PAEV_A1c_NEC_Histogram.png")

# -------------------------
# 7) JSON summary
# -------------------------
summary = {
    "ħ": ħ, "G": G, "Λ0": Λ0, "α0": α0, "χ": chi,
    "grid": {"N": N, "L": L, "dx": dx, "sigma_b": sigma_b},
    "timing": {"T_steps": T_steps, "dt": dt},
    "metrics": {
        "NEC_time_mean": NEC_time_mean,
        "NEC_time_min": NEC_time_min,
        "frac_exotic": frac_exotic,
        "dSdt_tail_mean": dSdt_tail_mean
    },
    "classification": classification,
    "files": {
        "nec_plot": "PAEV_A1c_NEC_TimeSeries.png",
        "entropy_plot": "PAEV_A1c_EntropySlope.png",
        "bubble_profile_plot": "PAEV_A1c_BubbleProfile.png",
        "nec_hist": "PAEV_A1c_NEC_Histogram.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = Path("backend/modules/knowledge/A1c_antigravity_bubble.json")
save_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved -> {save_path}")