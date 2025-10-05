#!/usr/bin/env python3
"""
Test C7 — Curvature Orbital Dynamics (Soft Coupling)
Simulates two curvature 'masses' orbiting due to deterministic rewrite geometry.
Baseline model: smooth, stable, non-chaotic orbital behavior.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ------------------ helpers ------------------

def gaussian_2d(x, y, x0, y0, sigma):
    """Return normalized Gaussian centered at (x0, y0)."""
    return np.exp(-((x - x0)**2 + (y - y0)**2) / (2 * sigma**2))

def compute_force(X, Y, p, sigma):
    """Compute gradient of curvature field at point p."""
    gx = -(X - p[0]) / (sigma**2) * np.exp(-((X - p[0])**2 + (Y - p[1])**2) / (2 * sigma**2))
    gy = -(Y - p[1]) / (sigma**2) * np.exp(-((X - p[0])**2 + (Y - p[1])**2) / (2 * sigma**2))
    return gx, gy

# ------------------ main simulation ------------------

def run_orbital_sim(N=121, steps=400, dt=0.1, eta=0.015, sigma=5.0):
    x = np.linspace(-N/2, N/2, N)
    y = np.linspace(-N/2, N/2, N)
    X, Y = np.meshgrid(x, y)

    # initial curvature lumps (masses)
    p1 = np.array([-15.0, 0.0])
    p2 = np.array([15.0, 0.0])
    v1 = np.array([0.0, 0.30])
    v2 = np.array([0.0, -0.30])

    frames = []
    E_total = []

    for t in range(steps):
        # curvature field = sum of two Gaussian bumps
        kappa = gaussian_2d(X, Y, *p1, sigma) + gaussian_2d(X, Y, *p2, sigma)

        # gradient-based force (each feels attraction toward total curvature)
        gx1, gy1 = compute_force(X, Y, p1, sigma)
        gx2, gy2 = compute_force(X, Y, p2, sigma)

        F1 = np.array([
            np.mean(gx1 * gaussian_2d(X, Y, *p2, sigma)),
            np.mean(gy1 * gaussian_2d(X, Y, *p2, sigma))
        ])
        F2 = np.array([
            np.mean(gx2 * gaussian_2d(X, Y, *p1, sigma)),
            np.mean(gy2 * gaussian_2d(X, Y, *p1, sigma))
        ])

        # update velocities and positions (soft coupling)
        v1 += eta * F1 * dt
        v2 += eta * F2 * dt
        p1 += v1 * dt
        p2 += v2 * dt

        # approximate "energy"
        E_kin = 0.5 * (np.linalg.norm(v1)**2 + np.linalg.norm(v2)**2)
        E_pot = np.mean(kappa)
        E_total.append(E_kin + E_pot)

        if t % 5 == 0:
            frames.append(kappa.copy())

    return np.array(frames), E_total, (x, y)

# ------------------ visualization ------------------

def main():
    frames, E_total, (x, y) = run_orbital_sim()
    print("✅ Test C7 — Curvature Orbital Dynamics (soft) complete.")
    print(f"Frames: {len(frames)}, Energy mean={np.mean(E_total):.4e}, std={np.std(E_total):.4e}")

    # --- Animation ---
    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(frames[0], cmap='inferno', extent=[x.min(), x.max(), y.min(), y.max()])
    ax.set_title("Test C7 — Curvature Orbital Dynamics (Photon Algebra)")
    def update(i):
        im.set_data(frames[i])
        ax.set_title(f"t={i*5}")
        return [im]
    ani = FuncAnimation(fig, update, frames=len(frames), interval=80, blit=True)
    ani.save("PAEV_TestC7_OrbitalDynamics.gif", fps=15)
    plt.close(fig)
    print("✅ Saved animation to: PAEV_TestC7_OrbitalDynamics.gif")

    # --- Energy plot ---
    plt.figure(figsize=(6.4, 4.2))
    plt.plot(E_total, 'b-', lw=1.5)
    plt.title("Test C7 — Total Rewrite Energy (Soft Coupling)")
    plt.xlabel("Time step")
    plt.ylabel("E_total (arb. units)")
    plt.tight_layout()
    plt.savefig("PAEV_TestC7_Orbital_Energy.png", dpi=160)
    print("✅ Saved energy plot to: PAEV_TestC7_Orbital_Energy.png")

if __name__ == "__main__":
    main()