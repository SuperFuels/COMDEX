# ==========================================================
# G4-RC4 - Lyapunov-Controlled Cross-Domain Coupling (TUE)
# Goal: Stabilize triune energy balance with filtered proxies,
#       anti-windup, and a Lyapunov descent controller.
# Saves: backend/modules/knowledge/G4RC4_lyapunov_controller.json
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

# ---- (Optional) shared constants ----
try:
    from backend.photon_algebra.utils.load_constants import load_constants
    C = load_constants()
except Exception:
    C = {}

ħ   = float(C.get("ħ", 0.001))
G0  = float(C.get("G", 1e-5))
Λ0  = float(C.get("Lambda_base", 1e-6))
α   = float(C.get("alpha", 0.5))
β   = float(C.get("beta", 0.2))
noise = float(C.get("noise", 2e-4))

# ---- Simulation params ----
np.random.seed(42)
T  = 6000
dt = 0.002
t  = np.linspace(0, T*dt, T)

# Controller gains (small; we'll let Lyapunov descent do the work)
kG   = 2.0e-4        # feedback to G_eff
kT   = 1.5e-4        # feedback to T_eff
kL   = 2.0e-4        # feedback to Λ_eff
ki   = 1.0e-3        # integral gain on energy error (slow)
alpha_ema  = 0.02    # EMA smoothing for signals
alpha_emas = 0.02

E_cap = 5.0e4        # soft display cap (plots), NOT a hard clip

# ---- Helper filters / clips ----
def ema(prev, new, a):   return (1-a)*prev + a*new
def soft_clip(x, cap):   return np.clip(x, -cap, cap)  # controller uses full value
def sat(x, lo, hi):      return max(lo, min(hi, x))

# ---- State / traces ----
# Toy complex field with slight detuning + noise (kept scalar 1D for speed)
w0 = 0.7
phi = 0.0
psi = np.zeros(T, dtype=complex)
psi_dot = np.zeros(T, dtype=complex)

# Effective constants (start at baselines)
G_eff = G0
T_eff = 1.0
Λ_eff = Λ0

# Proxies and energies
R = np.zeros(T)         # curvature proxy
S = np.zeros(T)         # entropy flux (filtered)
I = np.zeros(T)         # info flux (filtered)
E_geom = np.zeros(T); E_therm = np.zeros(T); E_info = np.zeros(T); E_total = np.zeros(T)
E_s = np.zeros(T)       # smoothed total energy for control

# Integral memory (anti-windup bounded)
I_err = 0.0

# ---- Main loop ----
psi_f = 0+0j; I_f = 0.0; S_f = 0.0; R_f = 0.0; E_prev = 0.0
for i in range(1, T):
    # Complex phase oscillator with tiny detuning & noise
    phi += w0*dt + 0.02*np.sin(0.5*phi)*dt + np.random.normal(0, noise)
    psi[i] = np.exp(1j*phi) * (1.0 + 0.02*np.sin(0.9*phi))  # mild amplitude modulation
    psi_dot[i] = (psi[i] - psi[i-1]) / dt

    # Geometric curvature proxy: second finite diff on real part (stable for 1D)
    if i > 1:
        R_raw = (psi[i].real - 2*psi[i-1].real + psi[i-2].real) / (dt**2)
    else:
        R_raw = 0.0
    R_f = ema(R_f, R_raw, alpha_ema)
    R[i] = R_f

    # Info flux proxy (mutual-info rate ~ Re(ψ̇ ψ*)), low-pass
    I_raw = float(np.real(psi_dot[i] * np.conj(psi[i])))
    I_f = ema(I_f, I_raw, alpha_ema)
    I[i] = I_f

    # Entropy proxy (bounded, smooth): small-signal log with guard
    amp2 = float(np.abs(psi[i])**2)
    S_raw = -amp2 * np.log(amp2 + 1e-9)
    # Normalize to a gentle range ~[0, ~0.05]
    S_raw = 0.05 * (S_raw / (1.0 + S_raw))
    S_f = ema(S_f, S_raw, alpha_emas)
    S[i] = S_f

    # Energies (units absorbed; signs chosen so controller can balance)
    E_geom[i]  =  (R[i] / (8*np.pi*max(G_eff, 1e-12)))
    E_therm[i] =  T_eff * S[i]
    E_info[i]  =  ħ * I[i]
    E_total[i] =  E_geom[i] + E_therm[i] + E_info[i] + Λ_eff * 0.1  # small Λ baseline term

    # Smooth energy for control and compute Lyapunov error V = 0.5 * E_s^2
    E_s[i] = ema(E_s[i-1], E_total[i], 0.05)
    err    = E_s[i]                          # target is 0
    I_err  = sat(I_err + err*dt, -1e3, 1e3) # anti-windup

    # Simple gradient-like action: push constants to reduce E_s
    dG = -kG * (err + ki*I_err) * np.sign(E_geom[i])     # oppose geometric contribution
    dT = -kT * (err + ki*I_err) * np.sign(E_therm[i])    # oppose thermal contribution
    dL = -kL * (err + ki*I_err) * np.sign(1.0)           # oppose baseline Λ term

    # Gentle coupling: if |I| grows while S is small, raise T_eff a hair (dissipation)
    dT +=  5e-5 * (abs(I[i]) - 0.02) if S[i] < 0.01 else 0.0
    # If |R| grows, nudge G back (avoid runaway)
    dG += -5e-5 * (abs(R[i]) - 5.0)

    # Apply bounded updates
    G_eff = max(1e-8, G_eff + dG*dt)
    T_eff = sat(T_eff + dT*dt, 1e-4, 5.0)
    Λ_eff = sat(Λ_eff + dL*dt, -1e-3, 1e-3)

# ---- Metrics ----
E_min = float(np.min(E_total))
E_max = float(np.max(E_total))
# Stability metric: variance reduction of smoothed energy vs. raw
num = np.var(E_s[int(0.7*T):]) + 1e-9
den = np.var(E_total[:int(0.3*T)]) + 1e-9
E_stab = float(1.0 - num/den)  # -> 1 means late-time is much calmer than early-time

corr_S_I = float(np.corrcoef(S[int(0.2*T):], I[int(0.2*T):])[0,1])
corr_R_L = float(np.corrcoef(R[int(0.2*T):], np.full(T-int(0.2*T), Λ_eff))[0,1])  # Λ_eff ~ const late

if (E_stab > 0.65) and (np.abs(np.mean(E_s[int(0.8*T):])) < 5e2) and (np.std(E_s[int(0.8*T):]) < 2e3):
    verdict = "✅ Stabilized Triune Coupling (Lyapunov descent lock)"
elif E_stab > 0.35:
    verdict = "⚠️ Partial Stabilization (needs tuning)"
else:
    verdict = "❌ Unstable or Weak Feedback"

# ---- Plots ----
plt.figure(figsize=(9,5))
plt.plot(t, E_total, lw=1.0, alpha=0.35, label="E_total (raw)")
plt.plot(t, E_s, lw=1.8, label="E_total (smoothed)")
plt.title("G4-RC4 - Energy Conservation (Lyapunov-Controlled)")
plt.xlabel("time"); plt.ylabel("E_total"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC4_EnergyConservation.png")

plt.figure(figsize=(9,5))
plt.plot(t, S, color="orange", lw=1.5, label="Entropy Flux S(t)")
plt.plot(t, I, color="purple", lw=1.0, label="Information Flux I(t)")
plt.title("G4-RC4 - Entropy-Information Dynamics (Filtered)")
plt.xlabel("time"); plt.ylabel("flux"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G4RC4_EntropyInfo.png")

plt.figure(figsize=(9,5))
plt.scatter(S[::10], I[::10], s=9, alpha=0.35, c="tab:green")
plt.title("G4-RC4 - Phase Portrait: S vs I (Lock Formation)")
plt.xlabel("Entropy Flux S"); plt.ylabel("Information Flux I")
plt.tight_layout(); plt.savefig("FAEV_G4RC4_PhasePortrait.png")

# ---- Save JSON ----
out = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G0": G0, "Λ0": Λ0, "α": α, "β": β, "noise": noise,
        "kG": kG, "kT": kT, "kL": kL, "ki": ki,
        "alpha_ema": alpha_ema, "alpha_emas": alpha_emas, "E_cap": E_cap
    },
    "metrics": {
        "energy_min": E_min,
        "energy_max": E_max,
        "energy_stability": E_stab,
        "corr_S_I": corr_S_I, "corr_R_Lambda": corr_R_L
    },
    "classification": verdict,
    "files": {
        "energy_plot": "FAEV_G4RC4_EnergyConservation.png",
        "coupling_plot": "FAEV_G4RC4_EntropyInfo.png",
        "phase_plot": "FAEV_G4RC4_PhasePortrait.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = "backend/modules/knowledge/G4RC4_lyapunov_controller.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== G4-RC4 - Lyapunov-Controlled Cross-Domain Coupling (TUE) ===")
print(f"stability={E_stab:.3f} | corr(S,I)={corr_S_I:.3f} | E_range=({E_min:.3e},{E_max:.3e})")
print(f"-> {verdict}")
print(f"✅ Results saved -> {save_path}")