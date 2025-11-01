# backend/photon_algebra/tests/paev_test_F15_matter_asymmetry.py
"""
F15 - Matter-Antimatter Asymmetry (Enhanced CP-like Bias Test)
---------------------------------------------------------------
Goal:
    Detect and quantify ψ1/ψ2 symmetry breaking (CP violation analogue)
    in the Tessaris photon-algebra feedback lattice.

Enhancements:
    ✅ Controlled CP-bias injector (phase_bias = 0.0025)
    ✅ Extended timesteps (steps = 2400)
    ✅ Improved classification (phase + energy asymmetry)
    ✅ Clean summary output (registry-ready)

Outputs:
    * PAEV_F15_Asymmetry.png
    * PAEV_F15_PhaseSkew.png
    * PAEV_F15_MutualInfo.png
    * PAEV_F15_DensityMaps.png
    * backend/modules/knowledge/F15_matter_asymmetry.json
"""

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# -------------------------
# 1) Load constants (v1.2 -> fallback)
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
Λ = float(constants.get("Λ", 1e-6))
α = float(constants.get("α", 0.5))
β = float(constants.get("β", 0.2))
np.random.seed(42)

# -------------------------
# 2) Grid setup
# -------------------------
N, L = 192, 6.0
x = np.linspace(-L, L, N)
X, Y = np.meshgrid(x, x)
dx = x[1] - x[0]

def laplacian_2d(Z):
    return (
        -4 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    ) / (dx**2)

def gaussian(cx, cy, s=0.9):
    return np.exp(-((X - cx)**2 + (Y - cy)**2) / (2 * s * s))

# Two curvature wells
kappa = -gaussian(-1.2, 0.0, 0.8) - gaussian(1.2, 0.0, 0.8)

# -------------------------
# 3) Initialize ψ1 / ψ2 fields
# -------------------------
base = gaussian(-1.2, 0.0, 0.9) + gaussian(1.2, 0.0, 0.9)
phase_seed = 0.35 * np.tanh(X / 1.2)
noise = 0.02 * (np.random.randn(N, N) + 1j * np.random.randn(N, N))

psi1 = base * np.exp(1j * phase_seed) * (1.0 + noise)
psi2 = base * np.exp(-1j * phase_seed) * (1.0 + np.conj(noise))
psi1_t = np.zeros_like(psi1, dtype=complex)
psi2_t = np.zeros_like(psi2, dtype=complex)

# -------------------------
# 4) Dynamics + feedback
# -------------------------
steps = 2400
dt = 0.006
phase_bias = 0.0025   # CP-bias injector
k_alpha, k_lambda = 0.002, 0.0015
alpha_t, Lambda_t = α, Λ
sponge = np.exp(-np.clip((np.sqrt(X**2 + Y**2) - (L * 0.9)), 0, None)**2 / (0.5**2))

def energy_proxy(psi):
    grad_x = (np.roll(psi, -1, 1) - np.roll(psi, 1, 1)) / (2 * dx)
    grad_y = (np.roll(psi, -1, 0) - np.roll(psi, 1, 0)) / (2 * dx)
    kinetic = np.mean(np.abs(grad_x)**2 + np.abs(grad_y)**2)
    potential = np.mean(np.real(kappa) * np.abs(psi)**2)
    damp = np.mean(np.abs(psi)**2)
    return float(ħ * kinetic + Lambda_t * potential + alpha_t * damp)

def mutual_info(ψa, ψb): return float(np.mean(np.real(ψa * np.conj(ψb))))
def cp_phase_skew(ψa, ψb): return float(np.angle(np.mean(ψa * np.conj(ψb)) + 1e-18))
def entropy(ψ): 
    amp2 = np.abs(ψ)**2 / (np.mean(np.abs(ψ)**2) + 1e-12)
    return float(-np.mean(amp2 * np.log(amp2 + 1e-12)))

# -------------------------
# 5) Run evolution
# -------------------------
A_trace, I_trace, phase_skew, E1_trace, E2_trace = [], [], [], [], []
S_prev = None

for t in range(steps):
    lap1, lap2 = laplacian_2d(psi1), laplacian_2d(psi2)

    psi1_tt = 1j * ħ * lap1 - alpha_t * psi1 + 1j * (Lambda_t + phase_bias) * kappa * psi1
    psi2_tt = 1j * ħ * lap2 - alpha_t * psi2 - 1j * (Lambda_t - phase_bias) * kappa * psi2

    psi1_t += dt * psi1_tt
    psi2_t += dt * psi2_tt
    psi1 += dt * psi1_t
    psi2 += dt * psi2_t

    psi1 *= sponge
    psi2 *= sponge

    E1, E2 = energy_proxy(psi1), energy_proxy(psi2)
    E1_trace.append(E1); E2_trace.append(E2)
    A_trace.append((E1 - E2) / max(E1 + E2, 1e-12))
    I_trace.append(mutual_info(psi1, psi2))
    phase_skew.append(cp_phase_skew(psi1, psi2))

    # entropy feedback
    S_now = 0.5 * (entropy(psi1) + entropy(psi2))
    dSdt = 0.0 if S_prev is None else (S_now - S_prev) / dt
    S_prev = S_now
    alpha_t = α - k_alpha * dSdt
    Lambda_t = Λ - k_lambda * dSdt

# -------------------------
# 6) Post-analysis
# -------------------------
tail = max(100, steps // 10)
A_tail_mean = float(np.mean(A_trace[-tail:]))
A_tail_abs = float(np.mean(np.abs(A_trace[-tail:])))
phase_tail_mean = float(np.mean(phase_skew[-tail:]))
I_drift = float(I_trace[-1] - I_trace[0])

# --- replace classification logic section ---
if A_tail_abs >= 0.01 and abs(phase_tail_mean) >= 0.2 and I_drift > 1e-4:
    classification = "✅ CP-like bias detected (energy + phase asymmetry)"
elif abs(phase_tail_mean) >= 0.8 and I_drift > 0.1:
    classification = "✅ Phase-dominant CP violation (low-energy asymmetry)"
elif A_tail_abs >= 0.005 and I_drift > 0:
    classification = "⚠️ Weak asymmetry (incipient CP bias)"
else:
    classification = "❌ No persistent asymmetry"

print("=== F15 - Matter-Antimatter Asymmetry (Enhanced) ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
print(f"A_tail_mean={A_tail_mean:.3e} | |A|_tail={A_tail_abs:.3e}")
print(f"phase_tail_mean={phase_tail_mean:.3e} | ΔI={I_drift:.3e}")
print(f"-> {classification}")

# -------------------------
# 7) Plots
# -------------------------
out_dir = Path(".")
plt.figure(figsize=(9, 4.5))
plt.plot(A_trace, lw=1.3); plt.axhline(0, color="k", ls="--", lw=0.8)
plt.title("F15 - Energy-Density Asymmetry A(t)")
plt.xlabel("time step"); plt.ylabel("A(t)")
plt.tight_layout(); plt.savefig(out_dir / "PAEV_F15_Asymmetry.png", dpi=160)

plt.figure(figsize=(9, 4.5))
plt.plot(phase_skew, lw=1.2); plt.axhline(0, color="k", ls="--", lw=0.8)
plt.title("F15 - CP-like Phase Skew Δφ(t)")
plt.xlabel("time step"); plt.ylabel("Δφ (radians)")
plt.tight_layout(); plt.savefig(out_dir / "PAEV_F15_PhaseSkew.png", dpi=160)

plt.figure(figsize=(9, 4.5))
plt.plot(I_trace, lw=1.2); plt.axhline(I_trace[0], color="k", ls=":", lw=0.8, label="initial I")
plt.title("F15 - Mutual-Information Proxy I(t)")
plt.xlabel("time step"); plt.ylabel("I = ⟨Re(ψ1ψ2*)⟩")
plt.legend(); plt.tight_layout(); plt.savefig(out_dir / "PAEV_F15_MutualInfo.png", dpi=160)

plt.figure(figsize=(10, 4.5))
plt.subplot(1, 2, 1); plt.imshow(np.abs(psi1), cmap="magma", extent=[-L, L, -L, L])
plt.colorbar(); plt.title("|ψ1|(final)")
plt.subplot(1, 2, 2); plt.imshow(np.abs(psi2), cmap="viridis", extent=[-L, L, -L, L])
plt.colorbar(); plt.title("|ψ2|(final)")
plt.tight_layout(); plt.savefig(out_dir / "PAEV_F15_DensityMaps.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_F15_Asymmetry.png")
print("  - PAEV_F15_PhaseSkew.png")
print("  - PAEV_F15_MutualInfo.png")
print("  - PAEV_F15_DensityMaps.png")

# -------------------------
# 8) Save knowledge card
# -------------------------
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "grid": {"N": N, "L": L, "dx": dx},
    "timing": {"steps": steps, "dt": dt},
    "metrics": {
        "A_tail_mean": A_tail_mean,
        "A_tail_abs": A_tail_abs,
        "phase_tail_mean": phase_tail_mean,
        "I_initial": float(I_trace[0]),
        "I_final": float(I_trace[-1]),
        "I_drift": I_drift,
        "E1_final": float(E1_trace[-1]),
        "E2_final": float(E2_trace[-1])
    },
    "classification": classification,
    "files": {
        "asymmetry_plot": "PAEV_F15_Asymmetry.png",
        "phase_plot": "PAEV_F15_PhaseSkew.png",
        "mi_plot": "PAEV_F15_MutualInfo.png",
        "density_maps": "PAEV_F15_DensityMaps.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

save_path = Path("backend/modules/knowledge/F15_matter_asymmetry.json")
save_path.write_text(json.dumps(summary, indent=2))
print(f"📄 Summary saved -> {save_path}")