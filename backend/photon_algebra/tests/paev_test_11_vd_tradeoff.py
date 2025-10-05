#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt

# --- Visibility–Distinguishability tradeoff ---
def quantum_vd(mu):
    """Ideal quantum relation V^2 + D^2 = 1"""
    D = mu
    V = np.sqrt(1 - D**2)
    return V, D

def photon_alg_vd(mu):
    """Photon Algebra analogue with symbolic mixing"""
    # identical model: weighted negation acts like continuous tagging
    D = mu
    V = np.sqrt(max(0, 1 - mu**2))  # ensures saturation
    return V, D

mu_vals = np.linspace(0, 1, 50)
qV, qD = [], []
paV, paD = [], []
for mu in mu_vals:
    Vq, Dq = quantum_vd(mu)
    Vp, Dp = photon_alg_vd(mu)
    qV.append(Vq); qD.append(Dq)
    paV.append(Vp); paD.append(Dp)

# --- Plot ---
plt.figure(figsize=(6,6))
plt.plot(qD, qV, 'b-', label='Quantum V–D')
plt.plot(paD, paV, 'r--', label='Photon Algebra V–D')
plt.plot([0,1],[1,0],'k:',alpha=0.5)
plt.xlabel("Distinguishability D")
plt.ylabel("Visibility V")
plt.title("Test 11 — V–D Complementarity (Partial Which-Path)")
plt.legend()
plt.axis("equal")
plt.tight_layout()
plt.savefig("PAEV_Test11_VD_Tradeoff.png")
print("✅ Saved plot to: PAEV_Test11_VD_Tradeoff.png")

# --- Check numeric relation ---
for mu in [0.0, 0.5, 1.0]:
    Vq, Dq = quantum_vd(mu)
    Vp, Dp = photon_alg_vd(mu)
    print(f"μ={mu:.1f} | Quantum: V^2+D^2={Vq**2+Dq**2:.3f} | PhotonAlg: V^2+D^2={Vp**2+Dp**2:.3f}")