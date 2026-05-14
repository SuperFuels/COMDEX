#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from math import cos, sin
from backend.photon_algebra.rewriter import normalize  # kept for consistency, not used here

# --- Quantum MZI with marker + eraser (unchanged) ---
def mzi_probs(phi, marker=False, erase=False):
    H_bs = (1/np.sqrt(2)) * np.array([[1, 1],
                                      [1,-1]], dtype=complex)
    I2  = np.eye(2, dtype=complex)
    X = np.array([[0,1],[1,0]], dtype=complex)
    PU = np.array([[1,0],[0,0]], dtype=complex)
    PL = np.array([[0,0],[0,1]], dtype=complex)

    psi_in = np.kron(np.array([[1],[0]],dtype=complex),
                     np.array([[1],[0]],dtype=complex))

    def phase(phi): return np.array([[np.exp(1j*phi),0],[0,1]],dtype=complex)
    def marker_op(on):
        if not on: return np.kron(I2,I2)
        return np.kron(PU,X) + np.kron(PL,I2)

    def eraser_op(on):
        if not on: return np.kron(I2,I2)
        ket = np.array([[1/np.sqrt(2)], [1/np.sqrt(2)]],dtype=complex)
        P = ket @ ket.conj().T
        return np.kron(I2,P)

    U = np.kron(H_bs,I2)
    U = np.kron(phase(phi),I2) @ U
    U = marker_op(marker) @ U
    U = np.kron(H_bs,I2) @ U
    U = eraser_op(erase) @ U

    psi = U @ psi_in
    psi_mat = psi.reshape(2,2)
    rho_path = psi_mat @ psi_mat.conj().T
    pU = np.real(rho_path[0,0])
    pL = np.real(rho_path[1,1])
    return float(pU), float(pL)

# --- Photon Algebra parametric analogue (FIX) ---
def photon_alg_intensity(phi, marker=False, erase=False):
    # coherence parameter epsilon
    eps = 1.0 if (marker and not erase) else 0.0
    # convex blend: coherent ((1+cos phi)/2) vs incoherent (1/2)
    I_D0 = 0.5 * ((1.0 - eps) * (1.0 + np.cos(phi)) + eps * 1.0)
    I_D1 = 1.0 - I_D0
    return float(I_D0), float(I_D1)

# --- Run sweep + plot ---
phi_vals = np.linspace(0,2*np.pi,400)
cases = [
    ("No marker", False, False, "b"),
    ("Marker ON", True,  False, "r"),
    ("Marker + Eraser", True, True, "g"),
]

plt.figure(figsize=(9,5.5))
for label, mark, erase, color in cases:
    qD0  = [mzi_probs(phi, marker=mark, erase=erase)[0] for phi in phi_vals]
    paD0 = [photon_alg_intensity(phi, marker=mark, erase=erase)[0] for phi in phi_vals]
    plt.plot(phi_vals, qD0,  color,      label=f"{label} (Quantum)")
    plt.plot(phi_vals, paD0, color+"--", label=f"{label} (PhotonAlg)")

plt.xlabel("Phase φ (radians)")
plt.ylabel("Detector D0 Intensity")
plt.title("Test 2 - Quantum Eraser (Mach-Zehnder)")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_Test2_Eraser.png")
print("✅ Saved plot to: PAEV_Test2_Eraser.png")

# --- Visibility table ---
def vis(y): 
    ymax, ymin = max(y), min(y)
    return (ymax - ymin) / (ymax + ymin) if (ymax + ymin) > 1e-12 else 0.0

for label, mark, erase, _ in cases:
    qV  = vis([mzi_probs(phi, marker=mark, erase=erase)[0] for phi in phi_vals])
    paV = vis([photon_alg_intensity(phi, marker=mark, erase=erase)[0] for phi in phi_vals])
    print(f"{label:15s}  Quantum V={qV:.3f}  PhotonAlg V={paV:.3f}")