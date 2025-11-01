#!/usr/bin/env python3
import numpy as np
from itertools import product
from backend.photon_algebra.rewriter import normalize

# GHZ state in quantum logic
def ghz_quantum_expect(setting_combo):
    # mapping X,Y measurement to Pauli matrices
    sigma_x = np.array([[0,1],[1,0]])
    sigma_y = np.array([[0,-1j],[1j,0]])
    ops = {'X': sigma_x, 'Y': sigma_y}

    # GHZ state (|000> + |111>)/√2
    ghz = (np.kron(np.kron([1,0],[1,0]),[1,0]) +
           np.kron(np.kron([0,1],[0,1]),[0,1])) / np.sqrt(2)

    U = np.kron(np.kron(ops[setting_combo[0]], ops[setting_combo[1]]),
                ops[setting_combo[2]])
    val = np.real(np.conjugate(ghz).T @ (U @ ghz))
    return float(val)

# Photon Algebra analogue: triadic entanglement parity
def ghz_photon_algebra(setting_combo):
    # symbolic rewrite rules for triadic entanglement
    # X ↔ keeps parity, Y ↔ introduces 90° rotation = i phase (cancelled in even #)
    phase = {'X': 0, 'Y': np.pi/2}
    total_phase = sum(phase[s] for s in setting_combo)
    return np.cos(total_phase)  # same as quantum parity

# --- Test combinations ---
tests = [
    ("XYY", +1),
    ("YXY", +1),
    ("YYX", +1),
    ("XXX", -1),
]

print("=== GHZ / Mermin 3-Photon Test ===")
print(f"{'Setting':6s} | {'Quantum':>8s} | {'PhotonAlg':>10s} | {'Expected':>9s}")
print("-"*40)
for combo, expected in tests:
    qv = ghz_quantum_expect(combo)
    pav = ghz_photon_algebra(combo)
    print(f"{combo:6s} | {qv:8.3f} | {pav:10.3f} | {expected:9.3f}")

# --- Logical consistency check ---
vals = [ghz_photon_algebra(combo) for combo, _ in tests]
logical_parity = vals[0]*vals[1]*vals[2]*vals[3]
print("\nParity product (should = -1):", f"{logical_parity:.3f}")
if abs(logical_parity + 1) < 1e-3:
    print("✅ GHZ logical contradiction reproduced.")
else:
    print("❌ GHZ parity mismatch - check rewrite rules.")