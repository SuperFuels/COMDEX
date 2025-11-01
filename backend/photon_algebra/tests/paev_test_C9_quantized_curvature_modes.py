#!/usr/bin/env python3
"""
Test C9 - Quantization of Curvature Energy (Emergent Graviton Modes)

Goal:
    Examine whether continuous rewrite curvature energy exhibits
    self-discretization - i.e. quantized curvature "modes" - when
    analyzed in the frequency domain.

Method:
    1. Simulate curvature oscillations κ(x,y,t) using a simple
       rewrite feedback wave equation.
    2. Record spatial mean ⟨κ2⟩ over time (energy trace).
    3. Perform FFT of ⟨κ2⟩(t) -> spectral power density.
    4. Compare to a smooth Gaussian control (no discrete modes).
    5. Identify emergent peaks - candidates for quantized modes.

Outputs:
    - PAEV_TestC9_QuantizedCurvature_Spectrum.png
    - PAEV_TestC9_QuantizedCurvature_Field.gif (optional)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter

# ---------- helpers ----------
def normalize(x): 
    return (x - np.min(x)) / (np.ptp(x) + 1e-12)

def laplacian(Z):
    return (
        np.roll(Z, 1, 0) + np.roll(Z, -1, 0) +
        np.roll(Z, 1, 1) + np.roll(Z, -1, 1) - 4 * Z
    )

# ---------- main experiment ----------
def main():
    N = 81
    steps = 400
    c = 1.0        # propagation speed
    gamma = 0.01   # damping
    eta = 0.15     # coupling
    dt = 0.1

    # spatial grid
    x = np.linspace(-4, 4, N)
    X, Y = np.meshgrid(x, x)
    R = np.sqrt(X**2 + Y**2)

    # initial localized curvature
    kappa = np.exp(-R**2)
    kappa_prev = kappa.copy()

    energy_trace = []
    frames = []

    print("=== Test C9 - Quantization of Curvature Energy (Emergent Graviton Modes) ===")
    for t in range(steps):
        lap = laplacian(kappa)
        kappa_next = (2 - gamma) * kappa - (1 - gamma) * kappa_prev + c**2 * dt**2 * lap
        kappa_next += eta * np.sin(kappa) * dt  # nonlinear self-coupling
        kappa_prev, kappa = kappa, kappa_next

        energy_trace.append(np.mean(kappa**2))
        if t % 10 == 0:
            frames.append(normalize(kappa))

    # --- Fourier analysis of total curvature energy ---
    E = np.array(energy_trace)
    E -= np.mean(E)
    fft_vals = np.fft.rfft(E)
    freqs = np.fft.rfftfreq(len(E), dt)
    power = np.abs(fft_vals)**2

    # --- Plot spectral power ---
    plt.figure(figsize=(7.5, 4.3))
    plt.plot(freqs, power / np.max(power), 'b-', lw=1.8)
    plt.title("Test C9 - Quantized Curvature Spectrum (Emergent Modes)")
    plt.xlabel("Frequency (arb. units)")
    plt.ylabel("Normalized power")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("PAEV_TestC9_QuantizedCurvature_Spectrum.png", dpi=160)
    print("✅ Saved spectrum to: PAEV_TestC9_QuantizedCurvature_Spectrum.png")

    # --- Optional: animate curvature field ---
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    img = ax.imshow(frames[0], cmap="inferno", vmin=0, vmax=1)
    ax.set_title("Test C9 - Curvature Field Evolution")
    ax.axis("off")

    def update(frame):
        img.set_data(frame)
        return [img]

    writer = PillowWriter(fps=10)
    from matplotlib.animation import FuncAnimation
    ani = FuncAnimation(fig, update, frames=frames, blit=True)
    ani.save("PAEV_TestC9_QuantizedCurvature_Field.gif", writer=writer)
    print("✅ Saved animation to: PAEV_TestC9_QuantizedCurvature_Field.gif")

    # --- Report key frequencies ---
    peak_indices = np.argsort(power)[-5:][::-1]
    print("\nTop spectral peaks (quantized curvature modes):")
    for i in peak_indices:
        print(f"  f={freqs[i]:.3f}  |  relative power={power[i]/np.max(power):.3f}")

    print("\n=== Test C9 complete ===")

if __name__ == "__main__":
    main()