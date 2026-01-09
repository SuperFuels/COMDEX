"""
A1d - Stabilized Anti-Gravity / Negative-Energy Bubble (Phase-IV)
-----------------------------------------------------------------
Goal:
    Achieve sustained NEC<0 fraction (>15%) and negative entropy slope tail.

Enhancements over A1c:
    * Stronger Lyapunov feedback (kL = 0.02)
    * Bursty anti-phase Λ(t) pulses (6-10% duty)
    * Bubble-local pressure relief pη = |∂xψ|2 - η|ψ|2
    * Optional second field ψ2 with anti-phase coupling γ_c
    * Exponential edge sponge (absorbing boundary)

Outputs:
    * PAEV_A1d_NEC_TimeSeries.png
    * PAEV_A1d_EntropySlope.png
    * PAEV_A1d_BubbleProfile.png
    * PAEV_A1d_NEC_Histogram.png
    * backend/modules/knowledge/A1d_antigravity_bubble.json
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
sigma_b = 2.5
bubble_gain = np.exp(-(x**2)/(2*sigma_b**2))

# Sponge at edges (absorbing)
sponge = np.exp(-((np.abs(x) - (L/2 - 5)) / 5.0)**2)
sponge = np.clip(sponge, 0.0, 1.0)

# -------------------------
# 3) Initialization
# -------------------------
psi1 = np.exp(-(x/6.0)**2) * np.exp(1j*0.4*x) * (1.0 + 0.01*np.random.randn(N))
psi2 = np.exp(-(x/6.0)**2) * np.exp(1j*(0.4*x + np.pi)) * (1.0 + 0.01*np.random.randn(N))
psi1 = psi1.astype(np.complex128)
psi2 = psi2.astype(np.complex128)
psi1_t = np.zeros_like(psi1)
psi2_t = np.zeros_like(psi2)

def laplacian_1d(z):
    return (np.roll(z, -1) - 2*z + np.roll(z, 1)) / (dx**2)

# -------------------------
# 4) Parameters
# -------------------------
T_steps = 6000
dt = 0.001
chi = 0.75                # nonlinear negative-pressure strength
eta = 0.04                # local pressure relief
gamma_c = 0.02            # inter-field coupling
k_alpha, k_lambda, k_i = 1e-2, 6e-3, 7e-3
kL = 2e-2                 # Lyapunov feedback
alpha = α0 * np.ones(N)
Lambda = Λ0 * np.ones(N)
i_accum = 0.0

# -------------------------
# 5) Traces
# -------------------------
S_trace, dSdt_trace = [], []
NEC_trace, NEC_min_trace = [], []
alpha_center_trace, Lambda_center_trace = [], []
S_prev_sm = None

def ema(prev, val, alpha=0.02):
    return (1-alpha)*prev + alpha*val if prev is not None else val

# -------------------------
# 6) Evolution loop
# -------------------------
for t in range(T_steps):
    lap1 = laplacian_1d(psi1)
    lap2 = laplacian_1d(psi2)

    # --- Bursty anti-phase Λ(t) pulses ---
    pulse = (t % 200) < 14
    Lambda_t = Λ0 * (1 - 0.5 * np.sin(2*np.pi*t/2000 + np.pi/2))
    if pulse:
        Lambda_t -= 0.6 * Λ0  # short downward pulse

    # --- Nonlinear and coupling terms ---
    nonlinear1 = -chi * np.abs(psi1)**2 * psi1
    nonlinear2 = -chi * np.abs(psi2)**2 * psi2
    coupling = gamma_c * bubble_gain * np.real(psi2 * np.conj(psi1))

    psi1_tt = 1j*ħ*lap1 - alpha*psi1 + 1j*Lambda_t*psi1 + nonlinear1 + coupling
    psi2_tt = 1j*ħ*lap2 - alpha*psi2 + 1j*(-Lambda_t)*psi2 + nonlinear2 + coupling

    psi1_t += dt * psi1_tt
    psi2_t += dt * psi2_tt
    psi1   += dt * psi1_t
    psi2   += dt * psi2_t

    # Apply sponge damping near edges
    psi1 *= sponge
    psi2 *= sponge

    # --- Entropy proxy (combined fields) ---
    amp2 = np.abs(psi1)**2 + np.abs(psi2)**2 + 1e-12
    S = -np.mean(amp2 * np.log(amp2))
    S_trace.append(S)

    if len(S_trace) > 1:
        dS = S_trace[-1] - S_trace[-2]
        dSdt_sm = ema(S_prev_sm, dS/dt, alpha=0.05)
        S_prev_sm = dSdt_sm
        dSdt_trace.append(dSdt_sm)
    else:
        dSdt_trace.append(0.0)

    # --- NEC proxy with local pressure relief ---
    grad_psi = (np.roll(psi1, -1) - np.roll(psi1, 1)) / (2*dx)
    rho = ħ * np.real(psi1_t * np.conj(psi1))
    p = np.abs(grad_psi)**2 - eta * np.abs(psi1)**2 * bubble_gain
    NEC = rho + p

    NEC_center = np.mean(NEC[bubble_gain > 0.1])
    NEC_trace.append(NEC_center)
    NEC_min_trace.append(np.min(NEC[bubble_gain > 0.1]))

    # --- Feedback control ---
    dSdt_local = np.mean(dSdt_trace[-10:]) if len(dSdt_trace) >= 10 else dSdt_trace[-1]
    i_accum = 0.995 * i_accum + dSdt_local
    drive = dSdt_local + k_i * i_accum

    alpha  = np.clip(α0 - k_alpha  * drive * bubble_gain, 0.05, 1.2)
    Lambda = np.clip(Λ0 - k_lambda * drive * bubble_gain, -0.05, 0.05)

    # Lyapunov push to reduce NEC>0
    nudger = -kL * np.sign(NEC_center) * bubble_gain
    alpha += nudger
    Lambda -= nudger

    alpha_center_trace.append(alpha[N//2])
    Lambda_center_trace.append(Lambda[N//2])

# -------------------------
# 7) Diagnostics
# -------------------------
NEC_time_mean = float(np.mean(NEC_trace))
NEC_time_min  = float(np.min(NEC_min_trace))
frac_exotic   = float(np.mean(np.array(NEC_min_trace) < 0.0))
dSdt_tail_mean = float(np.mean(dSdt_trace[-max(50, T_steps//20):]))

if (frac_exotic >= 0.15 and NEC_time_min <= -1e-3 and dSdt_tail_mean < 0):
    classification = "✅ Stable Exotic Bubble (NEC<0 sustained, entropy reversed)"
elif (frac_exotic >= 0.05 and NEC_time_min < -1e-4):
    classification = "⚠️ Transient Exotic Phase"
else:
    classification = "❌ No Exotic Phase"

print("=== A1d - Stabilized Anti-Gravity / Negative-Energy Bubble ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ0={Λ0:.3e}, α0={α0:.3f}, χ={chi:.2f}, η={eta:.2f}")
print(f"⟨NEC⟩_bubble = {NEC_time_mean:.3e} | min_t NEC = {NEC_time_min:.3e}")
print(f"fraction(NEC<0) = {frac_exotic:.2f} | tail ⟨dS/dt⟩ = {dSdt_tail_mean:.3e}")
print(f"-> {classification}")

# -------------------------
# 8) Plots
# -------------------------
out_dir = Path(".")
plt.figure(figsize=(9,4.5))
plt.plot(NEC_trace, lw=1.2, label="⟨NEC⟩ in bubble")
plt.plot(NEC_min_trace, lw=1.0, alpha=0.7, label="min(NEC) in bubble")
plt.axhline(0.0, color="k", ls="--", lw=0.8)
plt.title("A1d - NEC Proxy in Bubble (ρ + pη)")
plt.xlabel("time step"); plt.ylabel("NEC proxy")
plt.legend(); plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1d_NEC_TimeSeries.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(dSdt_trace, lw=1.2)
plt.axhline(0.0, color="k", ls="--", lw=0.8)
plt.title("A1d - Entropy Slope dS/dt (EMA)")
plt.xlabel("time step"); plt.ylabel("dS/dt")
plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1d_EntropySlope.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(alpha_center_trace, label="α(center)")
plt.plot(Lambda_center_trace, label="Λ(center)")
plt.title("A1d - Bubble Control Profiles at Center")
plt.xlabel("time step"); plt.ylabel("value")
plt.legend(); plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1d_BubbleProfile.png", dpi=160)

plt.figure(figsize=(6,4))
plt.hist(NEC_min_trace, bins=60, color="slateblue", alpha=0.75)
plt.axvline(0, color="k", lw=1, ls="--")
plt.title("A1d - Distribution of min(NEC) in Bubble")
plt.xlabel("NEC value"); plt.ylabel("frequency")
plt.tight_layout()
plt.savefig(out_dir / "PAEV_A1d_NEC_Histogram.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_A1d_NEC_TimeSeries.png")
print("  - PAEV_A1d_EntropySlope.png")
print("  - PAEV_A1d_BubbleProfile.png")
print("  - PAEV_A1d_NEC_Histogram.png")

# -------------------------
# 9) JSON summary
# -------------------------
summary = {
    "ħ": ħ, "G": G, "Λ0": Λ0, "α0": α0, "χ": chi, "η": eta, "γ_c": gamma_c,
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
        "nec_plot": "PAEV_A1d_NEC_TimeSeries.png",
        "entropy_plot": "PAEV_A1d_EntropySlope.png",
        "bubble_profile_plot": "PAEV_A1d_BubbleProfile.png",
        "nec_hist": "PAEV_A1d_NEC_Histogram.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = Path("backend/modules/knowledge/A1d_antigravity_bubble.json")
save_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved -> {save_path}")