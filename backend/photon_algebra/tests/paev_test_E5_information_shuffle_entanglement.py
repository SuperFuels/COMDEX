# -*- coding: utf-8 -*-
"""
E5 — Entanglement with Information Flow Shuffle
------------------------------------------------
Goal:
  Extend E2–E4 entanglement suite by introducing a stochastic "information shuffle"
  between entangled field pairs (ψ₁, ψ₂) to test whether randomized feedback exchange
  can reproduce a quantum-like Bell correlation (CHSH > 2).

Background:
  • E2 (Duan–Simon): CV entanglement detected ✅
  • E3 (Reid): EPR steering confirmed ✅
  • E4 (CHSH surrogate): Classical correlation only (S ≈ 2.0) ❌
  • E5 aims to explore whether stochastic information redistribution restores
    quantum-type nonlocal correlation without explicit measurement collapse.

"""

from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import matplotlib.pyplot as plt
import json

# ---------- Simulation constants ----------
ħ = 1e-3
Λ = 1e-6
α = 0.5
N = 192
L = 6.0
dx = L / N
steps = 1
dt = 0.006

# ---------- Field setup ----------
x = np.linspace(-L/2, L/2, N)
X, Y = np.meshgrid(x, x)
psi1 = np.exp(-((X+1.2)**2 + Y**2)/0.8) * (1 + 0.02*np.random.randn(N,N)*1j)
psi2 = np.exp(-((X-1.2)**2 + Y**2)/0.8) * (1 + 0.02*np.random.randn(N,N)*1j)

# ---------- Information shuffle ----------
def shuffle_info(psi1, psi2, p=0.5):
    """Randomly swap local amplitude data between psi1 and psi2"""
    mask = np.random.random(psi1.shape) > p
    psi1_new = psi1 * mask + psi2 * (~mask)
    psi2_new = psi2 * (~mask) + psi1 * mask
    return psi1_new, psi2_new

psi1, psi2 = shuffle_info(psi1, psi2, p=0.48)

# ---------- CHSH measurement ----------
def chsh_measure(psi1, psi2, angles):
    """Return correlation of field projections at given local phase angles"""
    a1, a2 = angles
    M1 = np.real(psi1 * np.exp(-1j * a1))
    M2 = np.real(psi2 * np.exp(-1j * a2))
    return np.mean(np.sign(M1) * np.sign(M2))

angles_deg = [(0,0), (0,45), (45,0), (45,45)]
angles = [(np.deg2rad(a1), np.deg2rad(a2)) for a1,a2 in angles_deg]

C = [chsh_measure(psi1, psi2, ang) for ang in angles]
S = abs(C[0] - C[1]) + abs(C[2] + C[3])

# ---------- Classification ----------
quantum_limit = 2.828
classical_limit = 2.0
classification = (
    "✅ Bell-type nonlocal correlation detected (quantum-like regime)"
    if S > 2.05 else
    "⚠️ Transitional correlation (near-classical)"
    if 1.95 < S <= 2.05 else
    "❌ No Bell violation (classical correlation)"
)

# ---------- Plot ----------
plt.figure(figsize=(7,5))
plt.bar(range(4), C, color='gray')
plt.axhline(0, color='black', lw=0.8)
plt.axhline(0.5, color='green', ls='--', label="Typical EPR Steering")
plt.axhline(1.0, color='blue', ls=':', label="Perfect Correlation")
plt.axhline(S/4, color='red', ls='-', label=f"CHSH ≈ {S:.3f}")
plt.title("E5 — Entanglement with Information Flow Shuffle")
plt.xlabel("Angle pair index"); plt.ylabel("Correlation")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_E5_InformationShuffle.png", dpi=160)

print("=== E5 — Entanglement with Information Flow Shuffle ===")
print(f"S = {S:.3f} → {classification}")
print("✅ Plot saved: PAEV_E5_InformationShuffle.png")

# ---------- Knowledge summary ----------
summary = {
    "ħ": ħ, "Λ": Λ, "α": α,
    "grid": {"N": N, "L": L, "dx": dx},
    "timing": {"steps": steps, "dt": dt},
    "metrics": {
        "S": float(S),
        "quantum_limit": quantum_limit,
        "classical_limit": classical_limit
    },
    "classification": classification,
    "files": {
        "chsh_plot": "PAEV_E5_InformationShuffle.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}
Path("backend/modules/knowledge/E5_information_shuffle_entanglement.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/E5_information_shuffle_entanglement.json")