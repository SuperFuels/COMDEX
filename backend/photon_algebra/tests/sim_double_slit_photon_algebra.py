# backend/photon_algebra/tests/sim_double_slit_photon_algebra.py
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# -------------------------------
# Quantum double-slit (scalar Fraunhofer)
# -------------------------------
def quantum_double_slit_intensity(x, lam=633e-9, L=1.0, d=50e-6, I0=1.0, coherence=1.0):
    """
    x: screen coordinate array (meters)
    lam: wavelength (m)
    L: slit-to-screen distance (m)
    d: slit separation (m)
    I0: single-slit normalized intensity baseline
    coherence: 0..1 fringe visibility multiplier (1 = perfect)
    Returns intensity at detector D(x).
    """
    # Relative phase difference Δφ(x) ≈ (2π/λ) * d * x / L  (small-angle)
    k = 2*np.pi/lam
    dphi = k * d * x / L
    # Ideal two equal slits: I(x) = I0 * [1 + coherence * cos(Δφ)] / 2
    # (We ignore single-slit envelope here for clarity)
    return 0.5 * I0 * (1.0 + coherence * np.cos(dphi))

# -------------------------------
# Photon Algebra parametric model
# -------------------------------
def photon_alg_visibility(marker_on=False, erased=False):
    """
    Map symbolic cases to visibility V:
    - No marker:      V = 1
    - Marker ON:      V = 0
    - Marker+Eraser:  V = 1
    (Same qualitative logic as in MZI demo; you can generalize later to partial erasure)
    """
    if marker_on and not erased:
        return 0.0
    return 1.0

def photon_alg_intensity(x, lam=633e-9, L=1.0, d=50e-6, I0=1.0, V=1.0):
    # Same cosine law but V comes from symbolic recombination ("x ⊕ ¬x -> ⊤" when coherence present)
    k = 2*np.pi/lam
    dphi = k * d * x / L
    return 0.5 * I0 * (1.0 + V * np.cos(dphi))

# -------------------------------
# Main sweep + plots
# -------------------------------
def main():
    # Geometry / sampling
    lam = 633e-9        # 633 nm (HeNe)
    L   = 1.0           # 1 m to screen
    d   = 50e-6         # 50 μm slit separation
    span = 10e-3        # ±10 mm screen window
    N   = 2000
    x   = np.linspace(-span, span, N)

    # Cases
    cases = [
        ("No marker",            dict(marker_on=False, erased=False), 1.0),
        ("Marker ON",            dict(marker_on=True,  erased=False), 0.0),
        ("Marker + Eraser",      dict(marker_on=True,  erased=True),  1.0),
    ]

    # Compute and collect
    results = []
    for label, flags, q_coh in cases:
        # Quantum prediction (coherence toggled by marker/eraser)
        Iq = quantum_double_slit_intensity(x, lam=lam, L=L, d=d, I0=1.0, coherence=q_coh)

        # Photon Algebra prediction (visibility from symbolic recombination)
        V  = photon_alg_visibility(**flags)
        Ia = photon_alg_intensity(x, lam=lam, L=L, d=d, I0=1.0, V=V)

        # Normalize both to 0..1 for clean comparison (optional)
        def norm01(y):
            ymin, ymax = float(y.min()), float(y.max())
            return (y - ymin) / (ymax - ymin + 1e-12)
        Iq_n = norm01(Iq)
        Ia_n = norm01(Ia)

        # Empirical visibilities (max-min)/(max+min)
        def visibility(y):
            ymax, ymin = float(y.max()), float(y.min())
            return (ymax - ymin) / (ymax + ymin + 1e-12)
        Vq = visibility(Iq)
        Va = visibility(Ia)

        results.append((label, Iq_n, Ia_n, Vq, Va))

    # ---------- Plot 1: intensity vs x ----------
    plt.figure(figsize=(10, 6))
    for i, (label, Iq_n, Ia_n, Vq, Va) in enumerate(results):
        # quantum
        if i == 0:
            plt.plot(x*1e3, Iq_n, label=f"{label} (Quantum)", linewidth=2)
        elif i == 1:
            plt.plot(x*1e3, Iq_n, label=f"{label} (Quantum)", color='C2', linewidth=2)
        else:
            plt.plot(x*1e3, Iq_n, label=f"{label} (Quantum)", color='C4', linewidth=2)

        # photon algebra (dashed)
        if i == 0:
            plt.plot(x*1e3, Ia_n, '--', label=f"{label} (PhotonAlg)", linewidth=2)
        elif i == 1:
            plt.plot(x*1e3, Ia_n, '--', label=f"{label} (PhotonAlg)", color='C2', linewidth=2)
        else:
            plt.plot(x*1e3, Ia_n, '--', label=f"{label} (PhotonAlg)", color='C4', linewidth=2)

    plt.title("Double Slit - Quantum vs Photon Algebra")
    plt.xlabel("Screen position x (mm)")
    plt.ylabel("Normalized intensity")
    plt.legend()
    plt.tight_layout()
    out1 = "double_slit_q_vs_photon.png"
    plt.savefig(out1, dpi=180)
    print(f"✅ Saved plot to {out1}")

    # ---------- Plot 2: visibility bars ----------
    labels = [r[0] for r in results]
    Vq_vals = [r[3] for r in results]
    Va_vals = [r[4] for r in results]

    X = np.arange(len(labels))
    w = 0.35

    plt.figure(figsize=(9, 5))
    plt.bar(X - w/2, Vq_vals, width=w, label="Quantum")
    plt.bar(X + w/2, Va_vals, width=w, label="PhotonAlg")
    plt.xticks(X, labels, rotation=0)
    plt.ylim(0, 1.05)
    plt.ylabel("Visibility V")
    plt.title("Double Slit - Fringe Visibility")
    plt.legend()
    plt.tight_layout()
    out2 = "double_slit_visibility_bars.png"
    plt.savefig(out2, dpi=180)
    print(f"✅ Saved plot to {out2}")

if __name__ == "__main__":
    main()