#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 3 — Double-Slit Interference + Quantum Eraser
"""

import numpy as np
import matplotlib.pyplot as plt
from backend.photon_algebra.rewriter import normalize

# -----------------------
# Quantum Model
# -----------------------

def quantum_double_slit(x, wavelength=500e-9, d=1e-3, L=1.0, marker=False, eraser=False):
    """
    Returns normalized intensity at screen position x.
    marker=True  → destroys interference (which-path info)
    eraser=True  → restores interference
    """
    k = 2 * np.pi / wavelength
    phi = k * d * x / L

    # Without marker: pure interference cos² pattern
    I = np.cos(phi / 2) ** 2

    if marker and not eraser:
        # Which-path info removes interference → flat
        I = np.ones_like(x) * 0.5
    elif marker and eraser:
        # Eraser restores interference (phase may be reduced)
        I = 0.5 * (1 + 0.8 * np.cos(phi))  # slightly lower visibility

    return I / np.max(I)


# -----------------------
# Photon Algebra Model
# -----------------------

def photon_algebra_double_slit(x, marker=False, eraser=False):
    """
    Symbolic reproduction via Photon Algebra:
    U⊕L superposition, marker → U⊗M ⊕ L, eraser → collapse to U⊕L.
    """
    results = []
    for xi in x:
        # phase depends on x
        phi = 2 * np.pi * xi / (max(x) - min(x))
        if marker and not eraser:
            expr = {"op": "⊕", "states": [{"op": "⊗", "states": ["U", "M"]}, "L"]}
        elif marker and eraser:
            expr = {"op": "⊕", "states": ["U", "L"]}
        else:
            expr = {"op": "⊕", "states": ["U", {"op": "¬", "state": "U"}]}  # interference
        n = normalize(expr)
        s = str(n)
        if "⊤" in s:
            I = 1.0
        elif "⊥" in s:
            I = 0.0
        elif "¬" in s:
            I = 0.5 * (1 + np.cos(phi))
        else:
            I = 0.5
        results.append(I)
    return np.array(results) / np.max(results)


# -----------------------
# Run Simulation
# -----------------------

x = np.linspace(-10e-3, 10e-3, 400)  # screen coordinate (m)

cases = [
    ("No marker", False, False),
    ("Marker ON", True, False),
    ("Marker + Eraser", True, True),
]

plt.figure(figsize=(10, 5))
colors = ["tab:blue", "tab:orange", "tab:green"]

for (label, mark, erase), color in zip(cases, colors):
    IQ = quantum_double_slit(x, marker=mark, eraser=erase)
    IPA = photon_algebra_double_slit(x, marker=mark, eraser=erase)
    plt.plot(x * 1e3, IQ, color=color, label=f"{label} (Quantum)")
    plt.plot(x * 1e3, IPA, color=color, linestyle="--", label=f"{label} (PhotonAlg)")

plt.title("Test 3 — Double-Slit Interference and Erasure")
plt.xlabel("Screen position x (mm)")
plt.ylabel("Normalized intensity")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_Test3_DoubleSlit.png", dpi=150)
print("✅ Saved plot to: PAEV_Test3_DoubleSlit.png")

# Visibility summary
def visibility(I):
    return (np.max(I) - np.min(I)) / (np.max(I) + np.min(I))

for label, mark, erase in cases:
    vQ = visibility(quantum_double_slit(x, marker=mark, eraser=erase))
    vPA = visibility(photon_algebra_double_slit(x, marker=mark, eraser=erase))
    print(f"{label:<18}  Quantum V={vQ:.3f}  PhotonAlg V={vPA:.3f}")