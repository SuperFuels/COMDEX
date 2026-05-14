# ==========================================================
# G3-RC5 - Phase-Locked Antigravity Bounce (Info + Entropy)
# Goal: lock negative-mass response to visible curvature phase,
#       keep energy soft-capped, and add entropy-aware damping.
# Saves: backend/modules/knowledge/G3RC5_phase_locked_bounce.json
# ==========================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

# ---- (Optional) pull shared constants, else fall back to defaults ----
try:
    from backend.photon_algebra.utils.load_constants import load_constants
    C = load_constants()
except Exception:
    C = {}

ħ   = float(C.get("ħ", 0.001))
G   = float(C.get("G", 1e-5))
Λ   = float(C.get("Lambda_base", 1e-6))
α   = float(C.get("alpha", 0.5))
β   = float(C.get("beta", 0.2))
ω0  = float(C.get("omega0", 0.18))
noise = float(C.get("noise", 6e-4))

# ---- Simulation params ----
np.random.seed(42)
T  = 6000
dt = 0.002

# Bounce / coupling controls
k_eq    = 0.035   # visible-hidden curvature equilibration
k_sync  = 0.05    # phase syncing strength
k_neg0  = 0.02    # base negative-mass drive
k_phase = 0.06    # NEW: phase-locked gain for antigravity
k_infoR = 0.015   # info feedback into curvature
k_infoM = 0.012   # info feedback into hidden mass
gamma_d = 0.002   # baseline dissipation (entropy)
kΛ      = 0.02    # adaptive Λ modulation
E_soft  = 3.0e4   # soft energy cap (not hard clip)

rho_c   = 1.0     # normalization

# ---- State arrays ----
t   = np.linspace(0, T*dt, T)
a   = np.zeros(T);    a[0] = 1.0
ad  = np.zeros(T);    ad[0] = -0.22
R   = np.zeros(T)     # visible curvature proxy
Rψ  = np.zeros(T)     # hidden curvature proxy
Mψ  = np.zeros(T);    Mψ[0] = 0.30
φ   = np.zeros(T);    ψ = np.zeros(T)   # phases
S   = np.zeros(T)     # entropy proxy 0..1
E   = np.zeros(T)     # unified energy (normalized)

# helpers
def clip_soft(x, cap):
    # soft cap via tanh shaping (keeps gradients smooth)
    return cap * np.tanh(x / max(cap, 1e-9))

for i in range(1, T):
    # --- information & phase metrics ---
    dI = np.cos(φ[i-1] - ψ[i-1])  # mutual information proxy (phase overlap)
    S[i] = min(1.0, 0.999*S[i-1] + 0.0003*(1 - dI))  # entropy builds when dephased

    # --- visible curvature proxy (simple FRW-like toy) ---
    R[i-1] = 0.5*a[i-1] - 0.7*np.sin(2*np.pi*(i*dt/6.5))  # oscillatory driving
    # --- hidden curvature follows, with equilibration & info feedback ---
    Rψ[i-1] = 0.6*Rψ[i-2] + 0.4*R[i-1] + k_eq*(R[i-1] - Rψ[i-2]) + k_infoR*(dI - 0.95)

    # --- phase evolution (φ visible, ψ hidden) with syncing ---
    φ[i] = φ[i-1] + (ω0 + 0.04*R[i-1] - 0.01*np.sin(φ[i-1]))*dt + np.random.normal(0, noise)
    ψ[i] = ψ[i-1] + (ω0 + 0.03*Rψ[i-1] - 0.01*np.sin(ψ[i-1]) + k_sync*np.sin(φ[i-1]-ψ[i-1]))*dt

    # --- adaptive negative-mass response locked to phase misalignment ---
    phase_err = np.sin(φ[i-1] - ψ[i-1])     # 0 when aligned, ±1 when quadrature
    k_neg = k_neg0 + k_phase*abs(phase_err) # stronger antigravity when out of phase

    # --- adaptive Λ (dark-energy like) nudged by energy and entropy ---
    Λ_eff = Λ * (1 + kΛ*(S[i] - 0.5))       # more dissipation when high entropy

    # --- hidden effective mass evolves with info feedback & damping ---
    dM = -k_infoM*(dI - 0.98) - 0.002*(Mψ[i-1] - 0.25) - 0.004*S[i]
    Mψ[i] = max(0.15, Mψ[i-1] + dM*dt)

    # --- unified energy (toy Tessaris split) ---
    E_geom = (c4 := 1.0) * R[i-1]            # (use c^4/8πG absorbed into units)
    E_ent  = S[i]                             # entropy part (scaled)
    E_info = ħ * (dI - 0.95)
    E_raw  = E_geom + E_ent + E_info + 0.5*Λ_eff*a[i-1]**2 - k_neg*R[i-1]
    E[i]   = clip_soft(E_raw, E_soft)

    # --- scale-factor dynamics with entropy-aware damping & antigravity ---
    # toy acceleration: matter (α), radiation-like (β), Λ, hidden coupling (k_neg), and damping
    a_dd = -α/(a[i-1]**2 + 1e-6) + β/(a[i-1]**4 + 1e-6) - Λ_eff*a[i-1] \
           - 0.015*R[i-1] + 0.012*Rψ[i-1] - k_neg*np.tanh(R[i-1]) \
           - (gamma_d*(1+2*S[i]))*ad[i-1] + 0.0008*np.cos(φ[i-1]-ψ[i-1])

    ad[i] = ad[i-1] + a_dd*dt
    a[i]  = max(1e-6, a[i-1] + ad[i]*dt)

# finalize last samples
R[-1] = R[-2]; Rψ[-1] = Rψ[-2]

# ---- Metrics & classification ----
a_min = float(np.min(a)); a_max = float(np.max(a))
bounce_idx = int(np.argmin(a))
cross_corr = float(np.corrcoef(R, Rψ)[0,1])
E_stab = float(np.std(E[-1500:]))
S_final = float(S[-1])

if (a_min > 0.28) and (cross_corr > 0.92) and (E_stab < 150):
    verdict = "✅ Phase-Locked Bounce (Coherent & Stable)"
elif (a_min > 0.24) and (cross_corr > 0.90) and (E_stab < 400):
    verdict = "⚠️ Partial Coupling (Near-Stable)"
else:
    verdict = "❌ Unstable or Decoupled"

# ---- Plots ----
plt.figure(figsize=(9,5))
plt.plot(t, a, lw=1.7)
plt.axvline(t[bounce_idx], ls='--', color='purple', alpha=0.7, label='min(a)')
plt.title("G3-RC5 - Scale Factor Evolution (Phase-Locked Bounce)")
plt.xlabel("time"); plt.ylabel("a(t)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC5_ScaleFactor.png")

plt.figure(figsize=(9,5))
plt.plot(t, R, label='R (visible)')
plt.plot(t, Rψ, label='Rψ (hidden)')
plt.title("G3-RC5 - Curvature Tracks (Phase-Locked)")
plt.xlabel("time"); plt.ylabel("curvature"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC5_Curvature.png")

plt.figure(figsize=(9,5))
plt.plot(t, E, label='Unified energy (soft-capped)')
plt.title("G3-RC5 - Unified Energy Evolution (Phase-Locked)")
plt.xlabel("time"); plt.ylabel("E_total (norm)"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC5_Energy.png")

plt.figure(figsize=(9,5))
plt.plot(t, np.cos(φ), label='cos(φ)')
plt.plot(t, np.cos(ψ), label='cos(ψ)')
plt.title("G3-RC5 - Phase Coherence")
plt.xlabel("time"); plt.ylabel("cosine phase"); plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G3RC5_Phase.png")

# ---- Save JSON ----
out = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β, "ω0": ω0, "noise": noise,
        "k_eq": k_eq, "k_sync": k_sync, "k_neg0": k_neg0, "k_phase": k_phase,
        "k_infoR": k_infoR, "k_infoM": k_infoM, "gamma_d": gamma_d,
        "kΛ": kΛ, "E_soft": E_soft, "rho_c": rho_c
    },
    "metrics": {
        "a_min": a_min, "a_max": a_max, "bounce_index": bounce_idx,
        "cross_correlation_R_Rψ": cross_corr, "energy_stability": E_stab,
        "entropy_final": S_final
    },
    "classification": verdict,
    "files": {
        "scale_plot": "FAEV_G3RC5_ScaleFactor.png",
        "curvature_plot": "FAEV_G3RC5_Curvature.png",
        "energy_plot": "FAEV_G3RC5_Energy.png",
        "phase_plot": "FAEV_G3RC5_Phase.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = "backend/modules/knowledge/G3RC5_phase_locked_bounce.json"
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== G3-RC5 - Phase-Locked Antigravity Bounce (Info + Entropy) ===")
print(f"a_min={a_min:.4f} | cross_corr={cross_corr:.3f} | E_stab={E_stab:.3e} | S_final={S_final:.3f}")
print(f"-> {verdict}")
print(f"✅ Results saved -> {save_path}")