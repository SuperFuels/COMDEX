# backend/photon_algebra/tests/sim_bell_photon_algebra.py
"""
Bell/CHSH - Quantum vs Photon Algebra (final working version)
"""

import numpy as np
import matplotlib.pyplot as plt

def deg(x):
    """Convert degrees to radians."""
    return np.deg2rad(x)

# --- Correlation models ---
def E_quantum(a, b):
    return np.cos(2 * (a - b))

def E_pa_quantum(a, b):
    return 2 * np.cos(a - b) ** 2 - 1  # equivalent to cos(2Δ)

def E_pa_local(a, b, L=1/np.sqrt(2)):
    return L * np.cos(2 * (a - b))

# --- compute CHSH S ---
def chsh_S(Efunc):
    a, a2, b, b2 = map(deg, [0, 45, 22.5, 67.5])
    Eab   = Efunc(a, b)
    Eabp  = Efunc(a, b2)
    Eapb  = Efunc(a2, b)
    Eapbp = Efunc(a2, b2)
    # Corrected: take absolute value of the CHSH combination
    return abs(Eab - Eabp + Eapb + Eapbp)

# --- Compute results ---
S_Q = chsh_S(E_quantum)
S_PAQ = chsh_S(E_pa_quantum)
S_PAL = chsh_S(lambda a, b: E_pa_local(a, b))

print("=== CHSH (Quantum vs Photon Algebra) ===")
print("Angles: a=0°, a'=45°, b=22.5°, b'=67.5°")
print(f"S (Quantum):     {S_Q:.3f}   [expected ≈ 2.828]")
print(f"S (PA-Quantum):  {S_PAQ:.3f}   [matches quantum]")
print(f"S (PA-Local):    {S_PAL:.3f}   [<= 2 by construction]")

# --- Plot correlations ---
phis = np.linspace(0, np.pi, 400)
E_q = np.cos(2 * phis)
E_paq = 2 * np.cos(phis) ** 2 - 1
L = 1 / np.sqrt(2)
E_pal = L * np.cos(2 * phis)

plt.figure(figsize=(10, 6))
plt.plot(phis, E_q, label="Quantum: E(Δ)=cos 2Δ")
plt.plot(phis, E_paq, "--", label="PA-Quantum: 2cos2Δ-1 (≡ cos 2Δ)")
plt.plot(phis, E_pal, ":", label=f"PA-Local: {L:.3f}*cos 2Δ (local cap)")

# Mark CHSH test points
a, a2, b, b2 = map(deg, [0, 45, 22.5, 67.5])
pairs = [(a, b), (a, b2), (a2, b), (a2, b2)]
labels = ["(a,b)", "(a,b')", "(a',b)", "(a',b')"]
for (A, B), label in zip(pairs, labels):
    Δ = abs(A - B)
    plt.scatter([Δ], [np.cos(2 * Δ)], color="black")
    plt.text(Δ, np.cos(2 * Δ) + 0.05, label, ha="center", fontsize=9)

plt.title("Bell/CHSH - Quantum vs Photon Algebra")
plt.xlabel("Analyzer angle difference Δ (radians)")
plt.ylabel("Correlation E")
plt.ylim(-1.05, 1.05)
plt.grid(alpha=0.3)
plt.legend(loc="lower left")
plt.tight_layout()
plt.savefig("bell_correlations.png", dpi=160)
print("✅ Saved plot to: bell_correlations.png")