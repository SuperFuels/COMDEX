#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mach-Zehnder Interferometer Simulation
Quantum vs Photon Algebra (Parametric)
Includes visibility (V) comparison metrics.
"""

import numpy as np
import matplotlib.pyplot as plt
from math import cos, sin
from backend.photon_algebra.rewriter import normalize

# ---------- Quantum model ----------
H_bs = (1/np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
I2 = np.eye(2, dtype=complex)

def phase(phi):
    return np.array([[np.exp(1j*phi), 0], [0, 1]], dtype=complex)

def which_path_marker(on=True):
    X = np.array([[0,1],[1,0]], dtype=complex)
    PU = np.array([[1,0],[0,0]], dtype=complex)
    PL = np.array([[0,0],[0,1]], dtype=complex)
    if not on:
        return np.kron(I2, I2)
    return np.kron(PU, X) + np.kron(PL, I2)

def eraser(theta):
    ket = np.array([[cos(theta)], [sin(theta)]], dtype=complex)
    Pth = ket @ ket.conj().T
    return np.kron(I2, Pth)

def mzi_output_probs(phi, marker_on=False, theta=None):
    psi_in = np.kron(np.array([[1],[0]]), np.array([[1],[0]]))
    U = np.kron(H_bs, I2)
    U = np.kron(phase(phi), I2) @ U
    U = which_path_marker(marker_on) @ U
    U = np.kron(H_bs, I2) @ U
    psi = U @ psi_in
    if theta is not None:
        E = eraser(theta)
        psi = E @ psi
        norm = np.linalg.norm(psi)
        if norm > 1e-12:
            psi /= norm
    psi_mat = psi.reshape(2, 2)
    rho_path = psi_mat @ psi_mat.conj().T
    pU = np.real(rho_path[0,0])
    pL = np.real(rho_path[1,1])
    return float(pU), float(pL)

# ---------- Photon Algebra (parametric) ----------
def photon_alg_intensity(phi, marker_on=False, theta=None):
    """
    Parametric mapping: logical complement ¬φ encodes phase φ.
    """
    phi_norm = (np.cos(phi) + 1) / 2
    if not marker_on:
        return phi_norm
    if marker_on and theta is None:
        return 0.5
    if marker_on and theta is not None:
        # restore interference with eraser (scaled by sin2θ)
        return 0.5 + 0.5 * np.cos(phi) * np.sin(theta)**2
    return phi_norm

# ---------- Simulation Sweep ----------
phis = np.linspace(0, 2*np.pi, 400)
cases = [
    ("No marker", False, None, "blue"),
    ("Marker ON", True, None, "red"),
    ("Marker+Eraser", True, np.pi/2, "green"),
]

results = []
plt.figure(figsize=(9,6))

for label, mark, th, color in cases:
    q_vals = [mzi_output_probs(phi, marker_on=mark, theta=th)[0] for phi in phis]
    a_vals = [photon_alg_intensity(phi, marker_on=mark, theta=th) for phi in phis]
    plt.plot(phis, q_vals, color=color, label=f"{label} (Quantum)")
    plt.plot(phis, a_vals, "--", color=color, label=f"{label} (PhotonAlg)")
    # Store for visibility
    Vq = (max(q_vals)-min(q_vals)) / (max(q_vals)+min(q_vals))
    Va = (max(a_vals)-min(a_vals)) / (max(a_vals)+min(a_vals))
    results.append((label, Vq, Va))

plt.title("Mach-Zehnder Interferometer - Quantum vs Photon Algebra (Parametric)")
plt.xlabel("Phase φ (radians)")
plt.ylabel("Detector D0 Intensity (normalized)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("mzi_visibility_comparison.png", dpi=150)
print("✅ Saved plot to: mzi_visibility_comparison.png\n")

# ---------- Visibility Summary ----------
print("=== Visibility Comparison ===")
print("Configuration".ljust(20), "Quantum V".ljust(15), "PhotonAlg V")
print("-"*50)
for label, Vq, Va in results:
    print(label.ljust(20), f"{Vq:.3f}".ljust(15), f"{Va:.3f}")