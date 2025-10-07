# backend/photon_algebra/tests/faev_test_G1RC4_adaptive_locking.py
# ================================================================
# G1-RC4 — Hidden Field Coupling (Adaptive Cross-Locking Controller)
# Goal: raise R↔Rψ correlation and tame unified-energy drift
# ================================================================

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

# --- constants loader (safe fallback) ---
try:
    from backend.photon_algebra.utils.load_constants import load_constants
    const = load_constants()
except Exception:
    const = {
        "ħ": 1e-3, "G": 1e-5, "Λ": 1e-6, "α": 0.5, "β": 0.2,
        "omega0": 0.18, "noise": 6e-4
    }

ħ, G, Λ, α, β = const.get("ħ",1e-3), const.get("G",1e-5), const.get("Λ",1e-6), const.get("α",0.5), const.get("β",0.2)
omega0, noise = const.get("omega0",0.18), const.get("noise",6e-4)

# --- sim params ---
np.random.seed(42)
T     = 4000
dt    = 0.002
t     = np.linspace(0, T*dt, T)

# controller params (new)
k_sync    = 0.035   # increases when R and Rψ diverge
k_damp    = 0.015   # energy-rate damping
k_info    = 0.003   # tiny phase info coupling φ→ψ
k_leak    = 0.002   # prevents runaway integral term
psi_gain  = 1.05
phi_damp  = 0.002
gamma     = 0.004   # mild Hubble-like damping on R
mu        = 0.02    # curvature→mass feedback

# --- state ---
R   = np.zeros(T)      # visible curvature proxy
Rψ  = np.zeros(T)      # hidden curvature proxy
E   = np.zeros(T)      # unified energy proxy
φ   = np.zeros(T)
ψ   = np.zeros(T)
R[0] = 0.0
Rψ[0]= 0.7
φ[0] = 0.0
ψ[0] = 0.01

integral_err = 0.0

def clipped(x, lo, hi): 
    return max(lo, min(hi, x))

for i in range(1, T):
    # --- phases (with tiny info-coupling nudge) ---
    dφ = (omega0 - phi_damp*np.sin(φ[i-1]))*dt + np.random.normal(0, noise)
    dψ = (omega0 + k_info*np.sin(φ[i-1]-ψ[i-1]))*dt + np.random.normal(0, noise*0.5)
    φ[i] = φ[i-1] + dφ
    ψ[i] = ψ[i-1] + dψ

    # --- target coupling strength based on divergence + phase misalign ---
    div  = (R[i-1] - Rψ[i-1])
    phase_err = np.sin(φ[i-1]-ψ[i-1])  # small near lock
    integral_err = (1.0 - k_leak)*integral_err + div*dt
    g_adapt = k_sync*(abs(div)) + 0.02*abs(phase_err) + 0.01*abs(integral_err)
    g_adapt = clipped(g_adapt, 0.0, 0.25)

    # --- raw drives (bounded polynomials) ---
    drive_R  = α*0.15 + mu*Rψ[i-1] - gamma*R[i-1] - 0.02*R[i-1]**3
    drive_Rψ = β*0.12 + mu*R[i-1]  - gamma*Rψ[i-1] - 0.02*Rψ[i-1]**3

    # --- cross-locking terms ---
    lock_R   = g_adapt*(Rψ[i-1]-R[i-1]) + 0.002*np.cos(φ[i-1]-ψ[i-1])
    lock_Rψ  = g_adapt*(R[i-1]-Rψ[i-1]) + 0.002*np.cos(φ[i-1]-ψ[i-1])

    # --- energy proxy (unified law, normalized) ---
    E_geom = (1.0/(8*np.pi*max(G,1e-12)))*R[i-1]
    E_th   = (1.0)*np.abs(np.cos(φ[i-1]))*0.25
    E_info = ħ*0.5*np.abs(np.sin(φ[i-1]-ψ[i-1]))
    E[i]   = E_geom + E_th + E_info

    # energy-rate damping factor (keeps things tame)
    dE_dt  = (E[i]-E[i-1])/dt if i>1 else 0.0
    rate_damp = 1.0/(1.0 + k_damp*abs(dE_dt))

    # --- integrate curvatures ---
    R[i]  = R[i-1]  + rate_damp*dt*(drive_R  + lock_R)
    Rψ[i] = Rψ[i-1] + rate_damp*dt*(drive_Rψ + lock_Rψ)*psi_gain

# --- metrics ---
def safe_std(x): 
    m = np.mean(x); return float(np.sqrt(np.mean((x-m)**2)))
cc   = float(np.corrcoef(R, Rψ)[0,1])
stab = safe_std(E) / (np.mean(E)+1e-9)
emin, emax = float(np.min(E)), float(np.max(E))

# --- classification ---
if cc>0.8 and stab<0.15:
    verdict = "✅ Coupled & Stable (adaptive lock)"
elif cc>0.6 and stab<0.35:
    verdict = "⚠️ Partially Coupled (marginal stability)"
else:
    verdict = "❌ Unstable Interaction (Decoupled Fields)"

# --- plots ---
plt.figure(figsize=(9,5))
plt.plot(t, R,  label="Visible curvature R")
plt.plot(t, Rψ, label="Hidden curvature Rψ")
plt.title("G1-RC4 — Hidden Field Coupling (Adaptive Locking)")
plt.xlabel("time"); plt.ylabel("curvature")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1RC4_CurvatureEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(t, E, label="Unified energy (norm)")
plt.title("G1-RC4 — Unified Energy Evolution (Adaptive-Damped)")
plt.xlabel("time"); plt.ylabel("E_total (norm)")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1RC4_EnergyEvolution.png")

plt.figure(figsize=(9,5))
plt.plot(t, np.cos(φ), label="cos(φ)")
plt.plot(t, np.cos(ψ), label="cos(ψ)")
plt.title("G1-RC4 — Phase Coherence Between φ and ψ (Adaptive)")
plt.xlabel("time"); plt.ylabel("cosine phase")
plt.legend(); plt.tight_layout()
plt.savefig("FAEV_G1RC4_PhaseCoherence.png")

# --- save JSON ---
out = {
    "dt": dt, "T": T,
    "constants": {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "omega0": omega0, "noise": noise,
        "gamma": gamma, "mu": mu,
        "k_sync": k_sync, "k_damp": k_damp, "k_info": k_info,
        "k_leak": k_leak, "psi_gain": psi_gain, "phi_damp": phi_damp
    },
    "metrics": {
        "cross_correlation_R_Rpsi": cc,
        "energy_stability": stab,
        "energy_min": emin,
        "energy_max": emax
    },
    "classification": verdict,
    "files": {
        "curvature_plot": "FAEV_G1RC4_CurvatureEvolution.png",
        "energy_plot": "FAEV_G1RC4_EnergyEvolution.png",
        "phase_plot": "FAEV_G1RC4_PhaseCoherence.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
with open("backend/modules/knowledge/G1RC4_coupling_adaptive.json","w") as f:
    json.dump(out, f, indent=2)

print("=== G1-RC4 — Hidden Field Coupling (Adaptive Cross-Locking Controller) ===")
print(f"cross_corr={cc:.3f} | stability={stab:.3f} | energy=({emin:.3e},{emax:.3e})")
print(f"→ {verdict}")
print("✅ Results saved → backend/modules/knowledge/G1RC4_coupling_adaptive.json")