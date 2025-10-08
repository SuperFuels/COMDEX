# -*- coding: utf-8 -*-
"""
E2 — Continuous-Variable Entanglement (Duan–Simon) via ER=EPR throat
--------------------------------------------------------------------
Goal:
  Detect inseparability of two coupled fields (ψ1, ψ2) using the Duan–Simon
  criterion on quadrature-like variables extracted from complex fields.

Witness (ħ-normalized):
  For balanced modes, define X_i = Re(ψ_i), P_i = Im(ψ_i).
  V = Var(X1 - X2) + Var(P1 + P2)  (spatial averages over throat mask)
  Inseparable if:  V < 2 * σ_vac   (σ_vac is the vacuum-like baseline)

Outputs:
  • PAEV_E2_DuanSimon_Timeseries.png
  • PAEV_E2_FieldMaps.png
  • backend/modules/knowledge/E2_cv_entanglement.json
"""
import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# --- constants (fallback chain)
CANDS = [
    Path("backend/modules/knowledge/constants_v1.2.json"),
    Path("backend/modules/knowledge/constants_v1.1.json"),
    Path("backend/modules/knowledge/constants_v1.0.json"),
]
for p in CANDS:
    if p.exists():
        K = json.loads(p.read_text()); break
else:
    K = {}
ħ = float(K.get("ħ", 1e-3))
Λ = float(K.get("Λ", 1e-6))
α = float(K.get("α", 0.5))

# --- grid & ER=EPR throat proxy
N = 192; L = 6.0
x = np.linspace(-L, L, N); X, Y = np.meshgrid(x, x)
dx = x[1] - x[0]
def lap2(Z): return (-4*Z + np.roll(Z,1,0)+np.roll(Z,-1,0)+np.roll(Z,1,1)+np.roll(Z,-1,1))/ (dx*dx)

def gaussian(cx, cy, s):
    return np.exp(-((X-cx)**2 + (Y-cy)**2)/(2*s*s))

# Two wells + throat mask
w1 = gaussian(-1.2, 0.0, 0.8)
w2 = gaussian( 1.2, 0.0, 0.8)
throat = np.exp(-((X/1.2)**2 + (Y/1.4)**2))
mask = (throat > 0.35).astype(float)

# Initial fields: conjugate-tilted (ER=EPR analogue)
phase = 0.35*np.tanh(X/1.2)
noise = 0.02*(np.random.randn(N,N) + 1j*np.random.randn(N,N))
base  = 0.9*w1 + 0.9*w2
psi1 = base * np.exp(1j*phase) * (1+noise)
psi2 = base * np.exp(-1j*phase) * (1+np.conj(noise))

# Dynamics with anti-phase Λ-coupling (encourages correlation locking)
T, dt = 1600, 0.006
alpha_t = α; Lambda_t = Λ
kα, kΛ = 0.0015, 0.001
sponge = np.exp(-np.clip((np.sqrt(X**2+Y**2) - 0.9*L), 0, None)**2 / 0.4**2)

def entropy(ψ):
    a2 = np.abs(ψ)**2; a2 /= (np.mean(a2)+1e-12)
    return float(-np.mean(a2*np.log(a2+1e-12)))

V_trace, Vx_trace, Vp_trace = [], [], []
S_trace = []

# Baseline “vacuum-like” variance from early transient (estimated online)
vac_buf = []

for t in range(T):
    lap1 = lap2(psi1); lap2_ = lap2(psi2)
    psi1_tt = 1j*ħ*lap1 - alpha_t*psi1 + 1j*Lambda_t*throat*psi1
    psi2_tt = 1j*ħ*lap2_ - alpha_t*psi2 - 1j*Lambda_t*throat*psi2
    psi1 += dt*psi1_tt; psi2 += dt*psi2_tt
    psi1 *= sponge; psi2 *= sponge

    # Quadratures in throat
    X1, P1 = np.real(psi1)[mask>0], np.imag(psi1)[mask>0]
    X2, P2 = np.real(psi2)[mask>0], np.imag(psi2)[mask>0]
    vX = np.var(X1 - X2); vP = np.var(P1 + P2)
    Vx_trace.append(vX); Vp_trace.append(vP); V_trace.append(vX+vP)

    # Online “vacuum” ref from the first 10% window
    if t < max(20, T//10): vac_buf.append(vX+vP)
    S_trace.append(0.5*(entropy(psi1)+entropy(psi2)))

    # Gentle feedback to keep regime bounded
    if t > 10:
        dSdt = S_trace[-1] - S_trace[-2]
        alpha_t = α - kα*dSdt
        Lambda_t = Λ - kΛ*dSdt

σ_vac = float(np.median(vac_buf)) if vac_buf else float(np.mean(V_trace[:50]))
V_tail = float(np.mean(V_trace[-max(50, T//10):]))

inseparable = V_tail < 2.0*σ_vac   # Duan–Simon (balanced, heuristic σ_vac)
classification = "✅ CV entanglement (Duan–Simon) detected" if inseparable else "❌ No inseparability (DS)"

print("=== E2 — CV Entanglement (Duan–Simon) ===")
print(f"σ_vac≈{σ_vac:.3e}, V_tail={V_tail:.3e} → {classification}")

# Plots
out = Path(".")
plt.figure(figsize=(10,4))
plt.plot(V_trace, label="V=Var(X1-X2)+Var(P1+P2)")
plt.axhline(2*σ_vac, ls="--", c="k", lw=1, label="DS threshold (heuristic)")
plt.title("E2 — Duan–Simon Inseparability (throat-averaged)")
plt.xlabel("step"); plt.ylabel("V"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_E2_DuanSimon_Timeseries.png", dpi=160)

plt.figure(figsize=(10,4))
plt.subplot(1,2,1); plt.imshow(np.abs(psi1), cmap="magma", extent=[-L,L,-L,L]); plt.title("|ψ1| (final)"); plt.colorbar()
plt.subplot(1,2,2); plt.imshow(np.abs(psi2), cmap="viridis", extent=[-L,L,-L,L]); plt.title("|ψ2| (final)"); plt.colorbar()
plt.tight_layout(); plt.savefig(out/"PAEV_E2_FieldMaps.png", dpi=160)

# Knowledge card
summary = {
  "ħ": ħ, "Λ": Λ, "α": α,
  "grid": {"N": N, "L": L, "dx": dx},
  "timing": {"steps": T, "dt": dt},
  "metrics": {"sigma_vac": σ_vac, "V_tail": V_tail, "DS_inseparable": bool(inseparable)},
  "classification": classification,
  "files": {
    "ds_plot": "PAEV_E2_DuanSimon_Timeseries.png",
    "maps": "PAEV_E2_FieldMaps.png"
  },
  "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/E2_cv_entanglement.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/E2_cv_entanglement.json")