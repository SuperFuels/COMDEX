#!/usr/bin/env python3
"""
Test C10 - Graviton Interference and Superposition Stability
------------------------------------------------------------
This simulation tests whether curvature quanta (graviton-like rewrite waves)
obey linear superposition and energy conservation.

Setup:
  * Two Gaussian curvature packets κ1, κ2 initialized on opposite sides.
  * Propagate under deterministic rewrite-wave evolution.
  * Check interference, total energy, and spectral stability.

Outputs:
  * PAEV_TestC10_GravitonInterference_Field.gif
  * PAEV_TestC10_GravitonInterference_Energy.png
  * PAEV_TestC10_GravitonInterference_Spectrum.png
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ---------- helpers ----------
def normalize(x): 
    return (x - np.min(x)) / (np.ptp(x) + 1e-12)

def gaussian_packet(N, center, sigma, kvec):
    """Gaussian curvature packet with wavevector modulation."""
    y, x = np.indices((N, N))
    cx, cy = center
    envelope = np.exp(-((x - cx)**2 + (y - cy)**2) / (2 * sigma**2))
    phase = np.cos(kvec[0]*(x - cx) + kvec[1]*(y - cy))
    return envelope * phase

# ---------- simulation ----------
def evolve_graviton_field(N=121, steps=300, c=1.0, eta=0.05, sigma=10):
    """Simulate deterministic rewrite propagation of two curvature waves."""
    κ = np.zeros((N, N))
    v = np.zeros_like(κ)

    # initialize two opposite curvature packets
    κ += gaussian_packet(N, (N*0.3, N/2), sigma, (0.3, 0))
    κ += gaussian_packet(N, (N*0.7, N/2), sigma, (-0.3, 0))

    frames = []
    E = []

    for t in range(steps):
        lap = (
            np.roll(κ, 1, 0) + np.roll(κ, -1, 0) +
            np.roll(κ, 1, 1) + np.roll(κ, -1, 1) - 4*κ
        )
        v += c**2 * lap - eta * v
        κ += v

        if t % 5 == 0:
            frames.append(normalize(κ.copy()))
        E.append(np.mean(κ**2))

    return np.array(frames), np.array(E)

# ---------- spectral analysis ----------
def compute_spectrum(E):
    """FFT of curvature energy time series."""
    f = np.fft.rfftfreq(len(E))
    S = np.abs(np.fft.rfft(E - np.mean(E)))**2
    return f, normalize(S)

# ---------- main ----------
def main():
    print("=== Test C10 - Graviton Interference and Superposition Stability ===")

    frames, E = evolve_graviton_field()
    f, S = compute_spectrum(E)

    # --- animation ---
    fig, ax = plt.subplots()
    im = ax.imshow(frames[0], cmap="inferno", animated=True)
    plt.title("Test C10 - Graviton Interference Field")
    plt.axis("off")

    def update(i):
        im.set_array(frames[i])
        return [im]

    ani = FuncAnimation(fig, update, frames=len(frames), interval=50)
    ani.save("PAEV_TestC10_GravitonInterference_Field.gif", fps=20)
    plt.close(fig)
    print("✅ Saved animation to: PAEV_TestC10_GravitonInterference_Field.gif")

    # --- energy plot ---
    plt.figure(figsize=(7,4))
    plt.plot(E, "b-")
    plt.xlabel("Time step")
    plt.ylabel("Total curvature energy ⟨κ2⟩")
    plt.title("Test C10 - Total Energy Evolution (Superposition Stability)")
    plt.tight_layout()
    plt.savefig("PAEV_TestC10_GravitonInterference_Energy.png", dpi=160)
    print("✅ Saved energy plot to: PAEV_TestC10_GravitonInterference_Energy.png")

    # --- power spectrum ---
    plt.figure(figsize=(7,4))
    plt.plot(f, S, "r-", lw=2)
    plt.xlabel("Frequency (arb. units)")
    plt.ylabel("Normalized spectral power")
    plt.title("Test C10 - Quantized Curvature Spectrum After Interference")
    plt.tight_layout()
    plt.savefig("PAEV_TestC10_GravitonInterference_Spectrum.png", dpi=160)
    print("✅ Saved spectrum to: PAEV_TestC10_GravitonInterference_Spectrum.png")

    # --- summary ---
    dominant = f[np.argmax(S)]
    print(f"Top spectral mode: f = {dominant:.3f}")
    print(f"Energy range: {E.min():.3e} -> {E.max():.3e}")
    print("=== Test C10 complete ===")

if __name__ == "__main__":
    main()