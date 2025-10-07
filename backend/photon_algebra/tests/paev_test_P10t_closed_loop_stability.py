import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
import json
from pathlib import Path

# ============================================
# P10t — Closed-Loop Stability Margin Analysis
# ============================================

# --- Load prior metrics (from P10r/s) ---
with open("backend/modules/knowledge/P10s_kernel_spectrum.json", "r") as f:
    ks = json.load(f)
with open("backend/modules/knowledge/P10r_resonance_memory_kernel.json", "r") as f:
    kr = json.load(f)

eta = ks["eta"]
f_peak = ks["f_peak"]
bw = ks["bw_3db"]
Q = ks["Q"]
tau_m = kr["metrics"]["tau_memory"]

# --- Linearized frequency response model ---
# Transfer function (first-order memory kernel approximation)
# G(jω) = 1 / (1 + j ω τ_m)
omega = np.logspace(-2, 3, 500)
G = 1 / (1 + 1j * omega * tau_m)

# Closed-loop open transfer gain (scaled by effective coupling)
K_global = 0.12
G_open = K_global * G

mag = np.abs(G_open)
phase = np.angle(G_open, deg=True)

# Gain crossover where |G| = 1
idx_cross = np.argmin(np.abs(mag - 1))
omega_gc = omega[idx_cross]
phase_gc = phase[idx_cross]

# Phase crossover where ∠G = -180°
idx_pc = np.argmin(np.abs(phase + 180))
omega_pc = omega[idx_pc]
mag_pc = mag[idx_pc]

# --- Margins ---
GM = 1/mag_pc if mag_pc != 0 else np.inf
PM = 180 + phase_gc

# --- Verdict ---
stable = (GM > 1.5) and (PM > 30)
classification = "✅ Stable" if stable else "⚠️ Marginal Stability"

# --- Plot Bode magnitude & phase ---
fig, ax = plt.subplots(2, 1, figsize=(8.5, 6.5), sharex=True)

ax[0].semilogx(omega, 20*np.log10(mag), lw=2)
ax[0].axhline(0, color='gray', ls='--')
ax[0].axvline(omega_gc, color='r', ls='--', label=f"ω_gc={omega_gc:.3f}")
ax[0].set_ylabel("Magnitude (dB)")
ax[0].grid(which='both', alpha=0.3)
ax[0].legend()

ax[1].semilogx(omega, phase, lw=2, color='purple')
ax[1].axhline(-180, color='gray', ls='--')
ax[1].axvline(omega_pc, color='orange', ls='--', label=f"ω_pc={omega_pc:.3f}")
ax[1].set_xlabel("Frequency ω (rad/s)")
ax[1].set_ylabel("Phase (deg)")
ax[1].grid(which='both', alpha=0.3)
ax[1].legend()

plt.suptitle("P10t — Closed-Loop Stability Margins")
plt.tight_layout()
plt.savefig("PAEV_P10t_ClosedLoop_Bode.png", dpi=240)
plt.close()

# --- Nyquist ---
plt.figure(figsize=(5.5, 5))
plt.plot(G_open.real, G_open.imag, lw=1.8)
plt.axhline(0, color='gray', lw=0.8)
plt.axvline(-1, color='r', ls='--')
plt.xlabel("Re(G)")
plt.ylabel("Im(G)")
plt.title("P10t — Nyquist Plot (Open-Loop Response)")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_P10t_ClosedLoop_Nyquist.png", dpi=240)
plt.close()

# --- Save results ---
out = {
    "eta": eta,
    "tau_memory": tau_m,
    "f_peak": f_peak,
    "Q": Q,
    "omega_gc": float(omega_gc),
    "omega_pc": float(omega_pc),
    "phase_gc": float(phase_gc),
    "mag_pc": float(mag_pc),
    "gain_margin": float(GM),
    "phase_margin": float(PM),
    "classification": classification,
    "files": {
        "bode_plot": "PAEV_P10t_ClosedLoop_Bode.png",
        "nyquist_plot": "PAEV_P10t_ClosedLoop_Nyquist.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
with open("backend/modules/knowledge/P10t_closed_loop_stability.json", "w") as f:
    json.dump(out, f, indent=2)

print("=== P10t — Closed-Loop Stability Margin ===")
print(f"Gain Margin = {GM:.2f}, Phase Margin = {PM:.1f}°, ω_gc={omega_gc:.3f}")
print(f"Verdict: {classification}")
print("✅ Results saved → backend/modules/knowledge/P10t_closed_loop_stability.json")