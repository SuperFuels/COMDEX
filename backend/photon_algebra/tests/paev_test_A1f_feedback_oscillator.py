"""
A1f — Adaptive Feedback Oscillator (Tessaris)
---------------------------------------------
Purpose:
    Follows A1e and adds adaptive timestep, noise cooling, and entropy-targeted
    control to sustain bounded, low-amplitude oscillations.
    This test demonstrates an adaptive nonlinear feedback bubble model.

Data policy:
    All quantities are abstract proxies for field stability and do not represent
    physical gravitational or quantum parameters.

This test auto-logs its results to:
    backend/modules/knowledge/A1f_feedback_oscillator.json
"""

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# --- Core parameters ---
ħ = 1e-3
G = 1e-5
Λ0 = 5e-6
α0 = 0.5
np.random.seed(321)

# --- Spatial grid ---
N, L = 512, 50.0
dx = L / N
x = np.linspace(-L/2, L/2, N)
sigma_b = 2.5
bubble_gain = np.exp(-(x**2)/(2*sigma_b**2))
sponge = np.exp(-((np.abs(x)-(L/2-5))/5.0)**2)
sponge = np.clip(sponge, 0.0, 1.0)

# --- Initialize field ---
psi = np.exp(-(x/6.0)**2) * np.exp(1j*0.3*x)
psi_t = np.zeros_like(psi, dtype=complex)

def laplacian_1d(z):
    return (np.roll(z, -1) - 2*z + np.roll(z, 1)) / (dx**2)

# --- Parameters ---
T_steps = 8000
dt_base = 0.001
chi = 1.0
k_alpha = 8e-3
k_lambda = 7e-3
k_entropy = 3e-3
noise_amp = 1e-3
alpha = α0 * np.ones(N)
Lambda = Λ0 * np.ones(N)

# --- Traces ---
S_trace, dSdt_trace = [], []
proxy_trace, proxy_min_trace = [], []
alpha_c_trace, Lambda_c_trace, noise_trace = [], [], []
S_prev_sm = None
dSdt_sm = 0.0   # <-- initialize safely

def ema(prev, val, alpha=0.02):
    return (1-alpha)*prev + alpha*val if prev is not None else val

# --- Evolution loop ---
for t in range(T_steps):
    lap = laplacian_1d(psi)
    grad = (np.roll(psi, -1) - np.roll(psi, 1)) / (2*dx)
    grad_rms = np.sqrt(np.mean(np.abs(grad)**2))
    dt = dt_base / (1.0 + 20*grad_rms)

    Lambda_t = Λ0 * (1 - 0.5*np.sin(2*np.pi*t/3000))
    psi_tt = 1j*ħ*lap - alpha*psi + 1j*Lambda_t*psi - chi*np.abs(psi)**2*psi
    psi_t += dt*psi_tt
    psi += dt*psi_t
    psi *= sponge

    amp2 = np.abs(psi)**2 + 1e-12
    S = -np.mean(amp2 * np.log(amp2))
    S_trace.append(S)

    if len(S_trace) > 1:
        dS = S_trace[-1] - S_trace[-2]
        dSdt_sm = ema(S_prev_sm, dS/dt, alpha=0.05)
        S_prev_sm = dSdt_sm
        dSdt_trace.append(dSdt_sm)
    else:
        dSdt_trace.append(0.0)
        dSdt_sm = 0.0

    proxy = ħ*np.real(psi_t*np.conj(psi)) + np.abs(grad)**2
    proxy_trace.append(np.mean(proxy[bubble_gain>0.1]))
    proxy_min_trace.append(np.min(proxy[bubble_gain>0.1]))

    # Adaptive noise cooling
    S_target = np.mean(S_trace[-200:]) if len(S_trace) > 200 else S_trace[-1]
    entropy_error = abs(S - S_target)
    noise_scale = noise_amp * np.exp(-entropy_error/0.01)
    psi += noise_scale * (np.random.randn(N) + 1j*np.random.randn(N))
    noise_trace.append(noise_scale)

    # Adaptive feedback — now safe with dSdt_sm fallback
    alpha = α0 - k_alpha*dSdt_sm*bubble_gain + k_entropy*entropy_error*bubble_gain
    Lambda = Λ0 - k_lambda*dSdt_sm*bubble_gain

    alpha_c_trace.append(alpha[N//2])
    Lambda_c_trace.append(Lambda_t)

# --- Metrics ---
proxy_mean = float(np.mean(proxy_trace))
proxy_min = float(np.min(proxy_min_trace))
entropy_tail = float(np.mean(dSdt_trace[-100:]))
noise_final = float(noise_trace[-1])
frac_dynamic = float(np.std(proxy_trace)/(abs(proxy_mean)+1e-12))

if frac_dynamic > 0.05 and abs(entropy_tail) < 1e-3:
    classification = "✅ Bounded oscillatory equilibrium"
else:
    classification = "⚠️ Weak or over-damped regime"

print("=== A1f — Adaptive Feedback Oscillator (Tessaris) ===")
print(f"ħ={ħ:.1e}, Λ0={Λ0:.1e}, α0={α0:.2f}")
print(f"<proxy>={proxy_mean:.3e} | min(proxy)={proxy_min:.3e}")
print(f"entropy_tail={entropy_tail:.3e}, noise_final={noise_final:.3e}")
print(f"→ {classification}")

# --- Plots ---
plt.figure(figsize=(9,4.5))
plt.plot(proxy_trace, label="proxy mean")
plt.plot(proxy_min_trace, label="proxy min", alpha=0.7)
plt.axhline(0, color="k", ls="--")
plt.legend(); plt.title("A1f — Proxy Dynamics")
plt.xlabel("time step"); plt.ylabel("proxy value")
plt.tight_layout(); plt.savefig("PAEV_A1f_Proxy_TimeSeries.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(dSdt_trace); plt.axhline(0, color="k", ls="--")
plt.title("A1f — Entropy Rate dS/dt (EMA)")
plt.xlabel("time step"); plt.ylabel("dS/dt")
plt.tight_layout(); plt.savefig("PAEV_A1f_EntropySlope.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(noise_trace)
plt.title("A1f — Noise Amplitude Schedule")
plt.xlabel("time step"); plt.ylabel("noise amplitude")
plt.tight_layout(); plt.savefig("PAEV_A1f_NoiseSchedule.png", dpi=160)

print("✅ Plots saved: PAEV_A1f_*")

# --- Knowledge record (Tessaris) ---
summary = {
    "tessaris_id": "A1f_feedback_oscillator",
    "title": "A1f — Adaptive Feedback Oscillator",
    "description": "Extends A1e by adding adaptive timestep and entropy-controlled noise cooling, demonstrating bounded oscillations under feedback. All quantities are abstract proxies.",
    "ħ": ħ,
    "Λ0": Λ0,
    "α0": α0,
    "grid": {"N": N, "L": L, "dx": dx, "sigma_b": sigma_b},
    "timing": {"T_steps": T_steps, "dt_base": dt_base},
    "metrics": {
        "proxy_mean": proxy_mean,
        "proxy_min": proxy_min,
        "entropy_tail": entropy_tail,
        "noise_final": noise_final,
        "frac_dynamic": frac_dynamic
    },
    "classification": classification,
    "outputs": {
        "proxy_plot": "PAEV_A1f_Proxy_TimeSeries.png",
        "entropy_plot": "PAEV_A1f_EntropySlope.png",
        "noise_plot": "PAEV_A1f_NoiseSchedule.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

out_path = Path("backend/modules/knowledge/A1f_feedback_oscillator.json")
out_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Knowledge saved → {out_path}")