# backend/photon_algebra/tests/paev_test_D1_dark_matter_geometry.py
"""
D1 - Dark Matter Geometry (Hidden-Sector Curvature Energy)
-----------------------------------------------------------
Goal:
  Quantify "invisible" curvature energy that influences geometry
  but is not encoded in ψ1, ψ2 field observables - a dark matter analogue.

Concept:
  ψ1, ψ2 : visible sector (standard photon algebra observers)
  ψ3, ψ4 : hidden sector (gravitationally coupled only)

Observables:
  * Visible curvature energy E_vis = ⟨|∇ψ1|2 + |∇ψ2|2⟩
  * Hidden curvature energy E_hid = ⟨|∇ψ3|2 + |∇ψ4|2⟩
  * Curvature difference ΔE = E_hid - E_vis
  * NEC proxy N = ⟨ρ + p⟩  (negative -> exotic curvature)
  * "Dark fraction" f_dark = E_hid / (E_vis + E_hid)
"""

import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# --- Load constants
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
Λ = float(constants.get("Λ", 1e-6))
α = float(constants.get("α", 0.5))

np.random.seed(42)

# --- Grid setup
N, L = 192, 6.0
x = np.linspace(-L, L, N)
X, Y = np.meshgrid(x, x)
dx = x[1] - x[0]

def laplacian(Z):
    return (-4*Z + np.roll(Z,1,0)+np.roll(Z,-1,0)+np.roll(Z,1,1)+np.roll(Z,-1,1)) / (dx**2)

def gaussian(cx, cy, s=0.9):
    return np.exp(-((X-cx)**2+(Y-cy)**2)/(2*s*s))

# --- Curvature wells (wormhole throat analogue)
kappa = -gaussian(-1.2, 0.0, 0.8) - gaussian(1.2, 0.0, 0.8)
base = gaussian(-1.2, 0.0, 0.9) + gaussian(1.2, 0.0, 0.9)

# --- Visible and hidden fields
psi1 = base * np.exp(1j*0.25*X) * (1+0.02*(np.random.randn(N,N)+1j*np.random.randn(N,N)))
psi2 = np.conj(psi1)
psi3 = 0.5 * base * (1+0.02*(np.random.randn(N,N)+1j*np.random.randn(N,N)))  # hidden
psi4 = np.conj(psi3)

# --- Simulation params
steps, dt = 1600, 0.006
Λ_vis, Λ_hid = Λ, Λ * 1.1  # slightly stronger curvature for hidden fields
sponge = np.exp(-np.clip((np.sqrt(X**2 + Y**2) - L*0.9), 0, None)**2 / (0.5**2))

def curvature_energy(psi):
    grad_x = (np.roll(psi, -1, 1) - np.roll(psi, 1, 1)) / (2*dx)
    grad_y = (np.roll(psi, -1, 0) - np.roll(psi, 1, 0)) / (2*dx)
    return np.mean(np.abs(grad_x)**2 + np.abs(grad_y)**2)

E_vis_trace, E_hid_trace, N_trace = [], [], []

for t in range(steps):
    lap1, lap2 = laplacian(psi1), laplacian(psi2)
    lap3, lap4 = laplacian(psi3), laplacian(psi4)

    # visible sector evolution (α damping + Λ curvature)
    psi1 += dt * (1j*ħ*lap1 - α*psi1 + 1j*Λ_vis*kappa*psi1)
    psi2 += dt * (1j*ħ*lap2 - α*psi2 - 1j*Λ_vis*kappa*psi2)

    # hidden sector evolution (no α coupling -> purely gravitational)
    psi3 += dt * (1j*ħ*lap3 + 1j*Λ_hid*kappa*psi3)
    psi4 += dt * (1j*ħ*lap4 - 1j*Λ_hid*kappa*psi4)

    for ψ in (psi1, psi2, psi3, psi4):
        ψ *= sponge

    E_vis = curvature_energy(psi1) + curvature_energy(psi2)
    E_hid = curvature_energy(psi3) + curvature_energy(psi4)
    E_vis_trace.append(E_vis)
    E_hid_trace.append(E_hid)
    N_trace.append(np.mean(np.real(kappa) * (np.abs(psi1)**2 - np.abs(psi3)**2)))

E_vis_final = float(np.mean(E_vis_trace[-100:]))
E_hid_final = float(np.mean(E_hid_trace[-100:]))
ΔE = E_hid_final - E_vis_final
f_dark = E_hid_final / (E_vis_final + E_hid_final)

classification = (
    "✅ Hidden curvature energy detected (dark mass analogue)"
    if f_dark > 0.3 else
    "⚠️ Weak hidden energy coupling"
)

print("=== D1 - Dark Matter Geometry Test ===")
print(f"E_vis={E_vis_final:.3e}, E_hid={E_hid_final:.3e}, f_dark={f_dark:.3f}")
print(f"NEC proxy mean={np.mean(N_trace[-200:]):.3e}")
print(f"-> {classification}")

# --- Plots
out_dir = Path(".")
plt.figure(figsize=(9,4.5))
plt.plot(E_vis_trace, label="Visible curvature energy")
plt.plot(E_hid_trace, label="Hidden curvature energy")
plt.xlabel("time step"); plt.ylabel("⟨|∇ψ|2⟩")
plt.legend(); plt.title("D1 - Visible vs Hidden Curvature Energy")
plt.tight_layout(); plt.savefig(out_dir/"PAEV_D1_EnergyTraces.png", dpi=160)

plt.figure(figsize=(9,4.5))
plt.plot(N_trace, lw=1.2)
plt.title("D1 - NEC Proxy (ρ+p)")
plt.xlabel("time step"); plt.ylabel("⟨ρ+p⟩")
plt.tight_layout(); plt.savefig(out_dir/"PAEV_D1_NECProxy.png", dpi=160)

plt.figure(figsize=(10,4.5))
plt.subplot(1,2,1)
plt.imshow(np.abs(psi1), cmap="magma", extent=[-L,L,-L,L]); plt.title("|ψ1|(final)")
plt.colorbar()
plt.subplot(1,2,2)
plt.imshow(np.abs(psi3), cmap="cividis", extent=[-L,L,-L,L]); plt.title("|ψ3|(final)")
plt.colorbar()
plt.tight_layout(); plt.savefig(out_dir/"PAEV_D1_VisibleHiddenMaps.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_D1_EnergyTraces.png")
print("  - PAEV_D1_NECProxy.png")
print("  - PAEV_D1_VisibleHiddenMaps.png")

# --- JSON knowledge card
summary = {
    "ħ": ħ, "Λ": Λ, "α": α,
    "grid": {"N": N, "L": L, "dx": dx},
    "timing": {"steps": steps, "dt": dt},
    "metrics": {
        "E_vis": E_vis_final,
        "E_hid": E_hid_final,
        "ΔE": ΔE,
        "f_dark": f_dark,
        "NEC_mean": float(np.mean(N_trace[-200:]))
    },
    "classification": classification,
    "files": {
        "energy_plot": "PAEV_D1_EnergyTraces.png",
        "nec_plot": "PAEV_D1_NECProxy.png",
        "maps": "PAEV_D1_VisibleHiddenMaps.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/D1_dark_matter_geometry.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved -> backend/modules/knowledge/D1_dark_matter_geometry.json")