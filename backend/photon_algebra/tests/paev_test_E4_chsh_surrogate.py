# -*- coding: utf-8 -*-
"""
E4 - CHSH Surrogate on Deterministic Fields (expect S <= 2)
----------------------------------------------------------
Goal:
  Emulate local measurement settings by projecting each field onto two local
  phase angles (a, a') and (b, b'), then sign-binning to ±1 outcomes.

Note:
  In this deterministic mean-field model, we expect NO violation (S <= 2).
  Useful to confirm classicality unless explicit stochastic measurement
  channels are introduced.

Outputs:
  * PAEV_E4_CHSH.png
  * backend/modules/knowledge/E4_chsh_surrogate.json
"""
import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

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

# Use final ψ1, ψ2 by constructing a coupled steady state like E2
N=192; L=6.0
x = np.linspace(-L,L,N); X,Y = np.meshgrid(x,x); dx=x[1]-x[0]
def gaussian(cx,cy,s): return np.exp(-((X-cx)**2+(Y-cy)**2)/(2*s*s))
phase = 0.35*np.tanh(X/1.2)
base = gaussian(-1.2,0,0.8)+gaussian(1.2,0,0.8)
ψ1 = base*np.exp(1j*phase)
ψ2 = base*np.exp(-1j*phase)

mask = (np.exp(-((X/1.2)**2+(Y/1.4)**2))>0.35)
z1 = (ψ1[mask]).ravel(); z2 = (ψ2[mask]).ravel()

def outcome(z, theta):
    # Project and sign-bin
    val = np.real(z*np.exp(-1j*theta))
    return np.sign(np.mean(val))

def corr(theta_a, theta_b):
    A = outcome(z1, theta_a); B = outcome(z2, theta_b)
    return float(A*B)

# Standard CHSH angles for maximal violation in QM
a, a2 = 0.0, np.pi/4
b, b2 = np.pi/8, -np.pi/8

S = abs( corr(a,b) - corr(a,b2) + corr(a2,b) + corr(a2,b2) )
classification = "❌ No Bell violation (classical correlation)" if S <= 2.0 else "⚠️ Apparent CHSH > 2"

print("=== E4 - CHSH Surrogate ===")
print(f"S = {S:.3f} -> {classification}")

plt.figure(figsize=(6,4))
plt.bar(["S"], [S]); plt.axhline(2.0, ls="--", c="k", lw=1, label="CHSH classical bound")
plt.title("E4 - CHSH Surrogate (deterministic field)"); plt.legend(); plt.tight_layout()
Path(".").mkdir(exist_ok=True)
plt.savefig("PAEV_E4_CHSH.png", dpi=160)

summary = {
  "ħ": ħ, "Λ": Λ, "α": α, "metrics": {"S": float(S)},
  "classification": classification,
  "files": {"chsh_plot": "PAEV_E4_CHSH.png"},
  "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/E4_chsh_surrogate.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved -> backend/modules/knowledge/E4_chsh_surrogate.json")