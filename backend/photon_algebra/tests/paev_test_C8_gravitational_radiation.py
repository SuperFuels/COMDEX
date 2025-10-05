#!/usr/bin/env python3
"""
Test C8 — Gravitational Radiation via Rewrite Energy Flow
Extends C7: two curvature sources orbit and emit curvature waves.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- FIXED normalize ---
def normalize(x):
    return (x - np.min(x)) / (np.ptp(x) + 1e-12)

def curvature_wave_update(kappa, vfield, eta=0.2, gamma=0.01):
    lap = (
        np.roll(kappa, 1, 0) + np.roll(kappa, -1, 0) +
        np.roll(kappa, 1, 1) + np.roll(kappa, -1, 1) -
        4 * kappa
    )
    dk = eta * lap - gamma * kappa + vfield
    return kappa + dk

def mass_source(N, centers, sigma=5.0, amp=1.0):
    y, x = np.indices((N, N))
    M = np.zeros((N, N))
    for (cx, cy, a) in centers:
        M += a * np.exp(-((x - cx)**2 + (y - cy)**2) / (2 * sigma**2))
    return M

def run_sim(N=101, steps=200, eta=0.2, gamma=0.01, orbit_radius=15, omega=0.05):
    kappa = np.zeros((N, N))
    energy = []
    for t in range(steps):
        # two orbiting sources
        cx1, cy1 = N//2 + orbit_radius*np.cos(omega*t), N//2 + orbit_radius*np.sin(omega*t)
        cx2, cy2 = N//2 - orbit_radius*np.cos(omega*t), N//2 - orbit_radius*np.sin(omega*t)
        vfield = mass_source(N, [(cx1, cy1, 1.0), (cx2, cy2, 1.0)], sigma=3.0)
        kappa = curvature_wave_update(kappa, vfield, eta, gamma)
        energy.append(np.mean(kappa**2))
    return np.array(energy), kappa

if __name__ == "__main__":
    N, steps = 101, 400
    energy, kappa = run_sim(N=N, steps=steps, eta=0.25, gamma=0.02)

    # --- Plot total energy decay ---
    plt.figure(figsize=(7,4))
    plt.plot(energy, "b-")
    plt.title("Test C8 — Gravitational Radiation via Rewrite Energy Flow")
    plt.xlabel("Time step")
    plt.ylabel("Mean curvature energy ⟨κ²⟩")
    plt.tight_layout()
    plt.savefig("PAEV_TestC8_GravitationalRadiation_Energy.png", dpi=160)
    print("✅ Saved energy plot to: PAEV_TestC8_GravitationalRadiation_Energy.png")

    # --- Final curvature snapshot ---
    plt.figure(figsize=(6,6))
    plt.imshow(normalize(kappa), cmap="inferno")
    plt.colorbar(label="Normalized κ(x,y)")
    plt.title("Test C8 — Gravitational Radiation Field (final frame)")
    plt.tight_layout()
    plt.savefig("PAEV_TestC8_GravitationalRadiation_Field.png", dpi=160)
    print("✅ Saved field image to: PAEV_TestC8_GravitationalRadiation_Field.png")

    print(f"Final ⟨κ²⟩={energy[-1]:.3e}, ΔE={energy[0]-energy[-1]:.3e}")
    print("=== Test C8 complete ===")