# -*- coding: utf-8 -*-
"""
E3 — EPR Steering (Reid criterion) in ER=EPR throat
---------------------------------------------------
Goal:
  Demonstrate EPR steering via conditional-variance product:
  V(X1|X2) * V(P1|P2) < (ħ/2)^2  → steering.

Construction:
  X = Re(ψ), P = Im(ψ) (balanced scaling). Conditional variances computed
  by linear regression over throat-averaged samples (per step).

Outputs:
  • PAEV_E3_Reid_Product.png
  • PAEV_E3_Conditional_Variances.png
  • backend/modules/knowledge/E3_epr_steering.json
"""
import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# constants
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
ħ = float(K.get("ħ", 1e-3)); Λ = float(K.get("Λ", 1e-6)); α = float(K.get("α", 0.5))

# grid & fields (same setup as E2 for comparability)
N = 192; L = 6.0
x = np.linspace(-L, L, N); X, Y = np.meshgrid(x, x); dx = x[1]-x[0]
def lap2(Z): return (-4*Z + np.roll(Z,1,0)+np.roll(Z,-1,0)+np.roll(Z,1,1)+np.roll(Z,-1,1))/ (dx*dx)
def gaussian(cx, cy, s): return np.exp(-((X-cx)**2 + (Y-cy)**2)/(2*s*s))

w1 = gaussian(-1.2,0,0.8); w2 = gaussian(1.2,0,0.8)
throat = np.exp(-((X/1.2)**2 + (Y/1.4)**2)); mask = (throat>0.35)
phase = 0.35*np.tanh(X/1.2)
noise = 0.02*(np.random.randn(N,N)+1j*np.random.randn(N,N))
base  = 0.9*w1+0.9*w2
psi1 = base*np.exp(1j*phase)*(1+noise)
psi2 = base*np.exp(-1j*phase)*(1+np.conj(noise))

T, dt = 1600, 0.006
alpha_t, Lambda_t = α, Λ
kα, kΛ = 0.0015, 0.001
sponge = np.exp(-np.clip((np.sqrt(X**2+Y**2)-0.9*L), 0, None)**2/0.4**2)

def cond_var(A, B):
    # V(A|B) = V(A - k*B) with optimal k = Cov(A,B)/Var(B)
    vB = np.var(B) + 1e-12
    k  = np.cov(A, B, bias=True)[0,1] / vB
    return float(np.var(A - k*B))

prod_trace, VX_trace, VP_trace = [], [], []

for t in range(T):
    lap1 = lap2(psi1); lap2_ = lap2(psi2)
    psi1 += dt*(1j*ħ*lap1 - alpha_t*psi1 + 1j*Lambda_t*throat*psi1)
    psi2 += dt*(1j*ħ*lap2_ - alpha_t*psi2 - 1j*Lambda_t*throat*psi2)
    psi1 *= sponge; psi2 *= sponge

    X1, P1 = np.real(psi1)[mask], np.imag(psi1)[mask]
    X2, P2 = np.real(psi2)[mask], np.imag(psi2)[mask]

    VX = cond_var(X1, X2)   # V(X1|X2)
    VP = cond_var(P1, P2)   # V(P1|P2)
    prod = VX * VP
    VX_trace.append(VX); VP_trace.append(VP); prod_trace.append(prod)

    # mild stabilizing feedback
    if t>4:
        dVX = VX_trace[-1]-VX_trace[-2]
        alpha_t = α - 0.0005*dVX
        Lambda_t = Λ - 0.0005*dVX

prod_tail = float(np.mean(prod_trace[-max(50, T//10):]))
threshold = (ħ/2.0)**2
steered = prod_tail < threshold

classification = "✅ EPR steering (Reid) detected" if steered else "❌ No EPR steering (Reid)"

print("=== E3 — EPR Steering (Reid) ===")
print(f"<V(X1|X2)V(P1|P2)>_tail = {prod_tail:.3e} vs (ħ/2)^2 = {threshold:.3e}")
print(f"→ {classification}")

out = Path(".")
plt.figure(figsize=(10,4))
plt.plot(prod_trace, lw=1.3, label="Reid product")
plt.axhline(threshold, ls="--", c="k", lw=1, label="(ħ/2)^2")
plt.title("E3 — Reid EPR Steering Product (throat-averaged)")
plt.xlabel("step"); plt.ylabel("Vx|* · Vp|*"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_E3_Reid_Product.png", dpi=160)

plt.figure(figsize=(10,4))
plt.plot(VX_trace, label="V(X1|X2)"); plt.plot(VP_trace, label="V(P1|P2)")
plt.title("E3 — Conditional Variances")
plt.xlabel("step"); plt.ylabel("variance"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_E3_Conditional_Variances.png", dpi=160)

summary = {
  "ħ": ħ, "Λ": Λ, "α": α,
  "grid": {"N": N, "L": L, "dx": dx},
  "timing": {"steps": T, "dt": dt},
  "metrics": {"reid_tail": prod_tail, "threshold": threshold, "steering": bool(steered)},
  "classification": classification,
  "files": {
    "reid_plot": "PAEV_E3_Reid_Product.png",
    "condvar_plot": "PAEV_E3_Conditional_Variances.png"
  },
  "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/E3_epr_steering.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/E3_epr_steering.json")