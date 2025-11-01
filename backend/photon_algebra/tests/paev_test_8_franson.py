#!/usr/bin/env python3
"""
Test 8 - Franson interferometer (energy-time entanglement)
Compares quantum coincidences vs Photon Algebra (PA) prediction.

Physics recap
-------------
Energy-time-entangled pairs enter two unbalanced MZIs (Alice, Bob).
Only indistinguishable EE/LL (early-early / late-late) paths contribute
to 2-photon interference. The coincidence rate varies as:

    C_QM(φA, φB) = 1/2 * [1 + V * cos(φA + φB)]

where V∈[0,1] is the coherence (dephasing reduces V).

PA mapping
----------
Encode the indistinguishable EE/LL branches as a dual pair that interferes.
Dephasing enters as a scalar coherence factor μ∈[0,1] multiplying visibility:

    C_PA(φA, φB; μ) = 1/2 * [1 + μ * cos(φA + φB)]

We sweep φΣ = φA + φB and plot C vs φΣ for several μ. We also print measured
visibilities from the generated curves (should match μ and V).
"""

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Quantum & Photon Algebra models
# -----------------------------

def C_quantum(phi_sum, V=1.0):
    """Quantum coincidence probability for Franson: 0.5 * (1 + V cos(phiA+phiB))."""
    return 0.5 * (1.0 + V * np.cos(phi_sum))

def C_photon_algebra(phi_sum, mu=1.0):
    """
    Photon Algebra (PA) coincidence.
    In PA, indistinguishable EE and LL branches form a dual structure whose
    interference strength is the coherence μ.
    """
    return 0.5 * (1.0 + mu * np.cos(phi_sum))

def visibility_from_curve(y):
    y = np.asarray(y)
    ymax, ymin = float(np.max(y)), float(np.min(y))
    if ymax + ymin == 0:
        return 0.0
    return (ymax - ymin) / (ymax + ymin)

# -----------------------------
# Sweep and plot
# -----------------------------
if __name__ == "__main__":
    phi = np.linspace(0, 2*np.pi, 721)   # high-res sweep of φΣ = φA+φB

    # Choose three dephasing/coherence levels to show effect on visibility
    cases = [
        ("High coherence", 1.00, "C0"),   # V=μ=1
        ("Medium coherence", 0.70, "C2"),
        ("Low coherence", 0.40, "C3"),
    ]

    plt.figure(figsize=(9,5.5))
    for label, coh, color in cases:
        cq = C_quantum(phi, V=coh)
        cp = C_photon_algebra(phi, mu=coh)

        # Plot: QM solid, PA dashed
        plt.plot(phi, cq, color=color, lw=2.2, label=f"{label} (Quantum)")
        plt.plot(phi, cp, color=color, lw=2.2, ls="--", label=f"{label} (PhotonAlg)")

        # Print visibilities measured from curves
        Vq = visibility_from_curve(cq)
        Vp = visibility_from_curve(cp)
        print(f"{label:18s}  Quantum V={Vq:.3f}  PhotonAlg V={Vp:.3f}")

    plt.title("Test 8 - Franson Interferometer (energy-time entanglement)")
    plt.xlabel("Phase sum φA + φB (radians)")
    plt.ylabel("Coincidence probability C(φA+φB)")
    plt.ylim(-0.05, 1.05)
    plt.xlim(0, 2*np.pi)
    plt.legend(ncol=2, frameon=True)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    out = "PAEV_Test8_Franson.png"
    plt.savefig(out, dpi=160)
    print(f"✅ Saved plot to: {out}")

    # Extra artifact: numeric check at the CHSH-optimal points (optional)
    for ang in [0, np.pi/2, np.pi, 3*np.pi/2]:
        v = C_photon_algebra(ang, mu=1.0)
        # Prints should line up with 0.5*(1 ± 1) = {0,1} at these points
        print(f"φΣ = {ang:5.2f} -> C_PA = {v:.3f}")