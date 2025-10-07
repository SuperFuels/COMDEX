"""
A1e — Nonlinear Feedback Stability Bubble Test
----------------------------------------------
Purpose:
    Explore stability and oscillatory regimes in coupled nonlinear fields with
    feedback control. Builds on A1d, but adds stochastic drive and stronger feedback
    to prevent numerical stagnation.

Interpretation:
    All quantities here (NEC, Λ, α) are abstract proxies for local stability energy
    and not physical gravitational quantities.

Key improvements:
    • Added small stochastic noise to avoid full damping
    • Slightly stronger feedback gains (kL, k_alpha)
    • Removes over-stabilizing term η
    • Uses smoother EMA tracking for entropy change
"""

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# -------------------------
# Constants and base params
# -------------------------
ħ = 1e-3
G = 1e-5
Λ0 = 5e-6
α0 = 0.5
np.random.seed(123)

N, L = 512, 50.0
dx = L / N
x = np.linspace(-L / 2, L / 2, N)
sigma_b = 2.5
bubble_gain = np.exp(-(x ** 2) / (2 * sigma_b ** 2))
sponge = np.exp(-((np.abs(x) - (L / 2 - 5)) / 5.0) ** 2)
sponge = np.clip(sponge, 0.0, 1.0)

# -------------------------
# Initialize fields
# -------------------------
psi1 = np.exp(-(x / 6.0) ** 2) * np.exp(1j * 0.4 * x)
psi2 = np.exp(-(x / 6.0) ** 2) * np.exp(1j * (0.4 * x + np.pi))
psi1_t = np.zeros_like(psi1, dtype=complex)
psi2_t = np.zeros_like(psi2, dtype=complex)

def laplacian_1d(z):
    return (np.roll(z, -1) - 2 * z + np.roll(z, 1)) / (dx ** 2)

# -------------------------
# Simulation parameters
# -------------------------
T_steps = 8000
dt = 0.001
chi = 1.1        # stronger nonlinear term
gamma_c = 0.05   # coupling
k_alpha = 1e-2
k_lambda = 8e-3
k_i = 7e-3
kL = 0.05
alpha = α0 * np.ones(N)
Lambda = Λ0 * np.ones(N)
i_accum = 0.0

# -------------------------
# Traces
# -------------------------
S_trace, dSdt_trace = [], []
NEC_trace, NEC_min_trace = [], []
alpha_center_trace, Lambda_center_trace = [], []
S_prev_sm = None

def ema(prev, val, alpha=0.02):
    return (1 - alpha) * prev + alpha * val if prev is not None else val

# -------------------------
# Evolution loop
# -------------------------
for t in range(T_steps):
    lap1 = laplacian_1d(psi1)
    lap2 = laplacian_1d(psi2)

    # Λ modulation with phase oscillation
    pulse = (t % 200) < 12
    Lambda_t = Λ0 * (1 - 0.6 * np.sin(2 * np.pi * t / 2500))
    if pulse:
        Lambda_t -= 0.7 * Λ0

    # Nonlinear terms and coupling
    nonlinear1 = -chi * np.abs(psi1) ** 2 * psi1
    nonlinear2 = -chi * np.abs(psi2) ** 2 * psi2
    coupling = gamma_c * bubble_gain * np.real(psi2 * np.conj(psi1))

    psi1_tt = 1j * ħ * lap1 - alpha * psi1 + 1j * Lambda_t * psi1 + nonlinear1 + coupling
    psi2_tt = 1j * ħ * lap2 - alpha * psi2 + 1j * (-Lambda_t) * psi2 + nonlinear2 + coupling

    psi1_t += dt * psi1_tt
    psi2_t += dt * psi2_tt
    psi1 += dt * psi1_t
    psi2 += dt * psi2_t

    # Add stochastic noise to keep dynamic
    psi1 += (1e-3) * (np.random.randn(N) + 1j * np.random.randn(N))
    psi2 += (1e-3) * (np.random.randn(N) + 1j * np.random.randn(N))

    # Sponge damping
    psi1 *= sponge
    psi2 *= sponge

    # Entropy proxy
    amp2 = np.abs(psi1) ** 2 + np.abs(psi2) ** 2 + 1e-12
    S = -np.mean(amp2 * np.log(amp2))
    S_trace.append(S)

    if len(S_trace) > 1:
        dS = S_trace[-1] - S_trace[-2]
        dSdt_sm = ema(S_prev_sm, dS / dt, alpha=0.05)
        S_prev_sm = dSdt_sm
        dSdt_trace.append(dSdt_sm)
    else:
        dSdt_trace.append(0.0)

    # Abstract NEC-like proxy
    grad_psi = (np.roll(psi1, -1) - np.roll(psi1, 1)) / (2 * dx)
    rho = ħ * np.real(psi1_t * np.conj(psi1))
    p = np.abs(grad_psi) ** 2 - 0.01 * np.abs(psi1) ** 2 * bubble_gain
    NEC = rho + p

    NEC_center = np.mean(NEC[bubble_gain > 0.1])
    NEC_trace.append(NEC_center)
    NEC_min_trace.append(np.min(NEC[bubble_gain > 0.1]))

    # Feedback
    dSdt_local = np.mean(dSdt_trace[-10:]) if len(dSdt_trace) > 10 else dSdt_trace[-1]
    i_accum = 0.995 * i_accum + dSdt_local
    drive = dSdt_local + k_i * i_accum

    alpha = np.clip(α0 - k_alpha * drive * bubble_gain, 0.05, 1.2)
    Lambda = np.clip(Λ0 - k_lambda * drive * bubble_gain, -0.05, 0.05)

    # Lyapunov drive
    alpha += -kL * np.sign(NEC_center) * bubble_gain
    Lambda += kL * np.sin(NEC_center * 50) * bubble_gain

    alpha_center_trace.append(alpha[N // 2])
    Lambda_center_trace.append(Lambda[N // 2])

# -------------------------
# Diagnostics
# -------------------------
NEC_time_mean = float(np.mean(NEC_trace))
NEC_time_min = float(np.min(NEC_min_trace))
frac_dynamic = float(np.std(NEC_trace) / (abs(NEC_time_mean) + 1e-12))
entropy_tail = float(np.mean(dSdt_trace[-max(50, T_steps // 20):]))

if frac_dynamic > 0.05 and abs(entropy_tail) > 1e-4:
    classification = "✅ Active dynamic regime achieved"
else:
    classification = "⚠️ Stable equilibrium / frozen state"

print("=== A1e — Nonlinear Feedback Stability Bubble Test ===")
print(f"ħ={ħ:.1e}, G={G:.1e}, Λ0={Λ0:.1e}, α0={α0:.2f}")
print(f"<NEC>={NEC_time_mean:.3e} | min(NEC)={NEC_time_min:.3e} | dynamic={frac_dynamic:.3f}")
print(f"entropy_tail={entropy_tail:.3e} → {classification}")

# -------------------------
# Plots
# -------------------------
plt.figure(figsize=(9,4.5))
plt.plot(NEC_trace, label="⟨proxy⟩ in bubble")
plt.plot(NEC_min_trace, label="min(proxy) in bubble", alpha=0.7)
plt.axhline(0, color='k', ls='--')
plt.title("A1e — Feedback Stability Proxy vs Time")
plt.xlabel("time step"); plt.ylabel("proxy value")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_A1e_Proxy_TimeSeries.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(dSdt_trace)
plt.axhline(0, color='k', ls='--')
plt.title("A1e — Entropy Rate dS/dt (EMA)")
plt.xlabel("time step"); plt.ylabel("dS/dt")
plt.tight_layout()
plt.savefig("PAEV_A1e_EntropySlope.png", dpi=160)

plt.figure(figsize=(6,4))
plt.hist(NEC_min_trace, bins=60, color="slateblue", alpha=0.75)
plt.axvline(0, color='k', lw=1, ls='--')
plt.title("A1e — Distribution of Proxy(min) in Bubble")
plt.xlabel("proxy value"); plt.ylabel("frequency")
plt.tight_layout()
plt.savefig("PAEV_A1e_Proxy_Histogram.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(alpha_center_trace, label="α(center)")
plt.plot(Lambda_center_trace, label="Λ(center)")
plt.title("A1e — Control Parameters at Center")
plt.xlabel("time step"); plt.ylabel("value")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_A1e_ControlProfiles.png", dpi=160)

print("✅ Plots saved → PAEV_A1e_*")

# -------------------------
# Save JSON summary
# -------------------------
summary = {
    "ħ": ħ, "G": G, "Λ0": Λ0, "α0": α0,
    "grid": {"N": N, "L": L, "dx": dx, "sigma_b": sigma_b},
    "timing": {"T_steps": T_steps, "dt": dt},
    "metrics": {
        "proxy_mean": NEC_time_mean,
        "proxy_min": NEC_time_min,
        "frac_dynamic": frac_dynamic,
        "entropy_tail": entropy_tail
    },
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/A1e_feedback_stability.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/A1e_feedback_stability.json")