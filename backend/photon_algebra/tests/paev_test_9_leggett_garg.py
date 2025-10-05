#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt

def C_ij(theta):
    # Quantum temporal correlation
    return np.cos(theta)

def K_quantum(theta):
    return 2 * np.cos(theta) - np.cos(2*theta)

def C_pa(theta, mu):
    # Photon Algebra analogue: suppress coherence by (1-μ)
    return (1 - mu) * np.cos(theta)

def K_pa(theta, mu):
    return 2*C_pa(theta,mu) - C_pa(2*theta,mu)

theta_vals = np.linspace(0, np.pi/2, 200)
mu_vals = [0.0, 0.5, 1.0]
colors = ["b","g","r"]

plt.figure(figsize=(8,5))
for mu, c in zip(mu_vals, colors):
    Kq = K_quantum(theta_vals)
    Kp = K_pa(theta_vals, mu)
    plt.plot(theta_vals, Kq, "k--", alpha=0.3) if mu==0 else None
    plt.plot(theta_vals, Kp, c, label=f"PA μ={mu}")
plt.axhline(1, color="k", linestyle=":", label="Macrorealistic bound")
plt.xlabel("Evolution angle θ")
plt.ylabel("K = C12 + C23 − C13")
plt.title("Test 9 — Leggett–Garg Inequality (Temporal Coherence)")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_Test9_LGI.png")
print("✅ Saved plot to: PAEV_Test9_LGI.png")

for mu in mu_vals:
    Kmax_q = np.max(K_quantum(theta_vals))
    Kmax_pa = np.max(K_pa(theta_vals, mu))
    print(f"μ={mu:.1f}  Quantum Kmax={Kmax_q:.3f}  PhotonAlg Kmax={Kmax_pa:.3f}")