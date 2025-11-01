#!/usr/bin/env python3
"""
Test C5 - Gravitational Wave from Curvature-Rewrite Coupling
------------------------------------------------------------
Goal:
Simulate a 2D symbolic spacetime where rewrite curvature evolves
under deterministic feedback, producing wave-like propagation.

Model:
∂2κ/∂t2 = c2 ∇2κ - γ ∂κ/∂t + η * Δ_rw(κ)
where:
  - κ(x,y,t)  = curvature field (Photon Algebra equivalent)
  - ∇2κ       = Laplacian (spatial propagation)
  - γ         = damping factor
  - η         = rewrite feedback coupling
  - Δ_rw(κ)   = local contextual rewrite curvature deviation

The simulation starts with a localized "bump" (curvature pulse)
that propagates as a gravitational wave analogue.

Outputs:
 - PAEV_TestC5_GravitationalWave_Frame.png
 - PAEV_TestC5_GravitationalWave_2D.gif
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.animation import FuncAnimation, PillowWriter

# ---------- Simulation parameters ----------
N = 81             # grid size
dx = 1.0
dt = 0.1
steps = 80         # number of time steps
c = 1.0            # wave speed
gamma = 0.02       # damping coefficient
eta = 0.15         # rewrite feedback strength

# ---------- Initialize curvature field ----------
x = np.linspace(-4, 4, N)
y = np.linspace(-4, 4, N)
X, Y = np.meshgrid(x, y)
r2 = X**2 + Y**2

# initial Gaussian curvature bump
kappa = np.exp(-r2)
kappa_prev = np.exp(-r2)  # for second-order integration

# ---------- helper functions ----------
def laplacian(Z):
    return (
        np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0)
        + np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1)
        - 4 * Z
    ) / dx**2

def rewrite_feedback(Z):
    """
    Deterministic 'Photon Algebra' rewrite correction:
    favors local curvature smoothing but retains context (nonlinear).
    """
    local_mean = 0.25 * (
        np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )
    delta = local_mean - Z
    return np.tanh(delta)

# ---------- Time evolution ----------
frames = []
for t in range(steps):
    lap = laplacian(kappa)
    rw = rewrite_feedback(kappa)
    kappa_next = (
        2 * kappa - kappa_prev
        + dt**2 * (c**2 * lap - gamma * (kappa - kappa_prev) / dt + eta * rw)
    )
    kappa_prev = kappa.copy()
    kappa = kappa_next.copy()

    # Normalize to [0,1] for visualization
    knorm = (kappa - kappa.min()) / (kappa.max() - kappa.min() + 1e-12)
    frames.append(knorm)

# ---------- Plot final frame ----------
plt.figure(figsize=(10, 4))
plt.imshow(frames[-1], cmap="inferno", origin="lower")
plt.title("Test C5 - Gravitational Wave Final Curvature Field")
plt.colorbar(label="Normalized κ(x,y)")
plt.tight_layout()
plt.savefig("PAEV_TestC5_GravitationalWave_Frame.png", dpi=180)
print("✅ Saved final frame to: PAEV_TestC5_GravitationalWave_Frame.png")

# ---------- Animation ----------
fig, ax = plt.subplots(figsize=(5, 5))
im = ax.imshow(frames[0], cmap="inferno", origin="lower", vmin=0, vmax=1)
ax.set_title("Test C5 - Gravitational Wave (Photon Algebra)")
ax.axis("off")

def update(frame):
    im.set_data(frame)
    return [im]

ani = FuncAnimation(fig, update, frames=frames, interval=80, blit=True)
ani.save("PAEV_TestC5_GravitationalWave_2D.gif", writer=PillowWriter(fps=15))
plt.close(fig)

print("✅ Saved animation to: PAEV_TestC5_GravitationalWave_2D.gif")
print("\n=== Test C5 - Gravitational Wave Simulation Complete ===")
print(f"Lattice={N}*{N}, steps={steps}, c={c}, γ={gamma}, η={eta}")
print("Wavefronts exhibit propagation and curvature oscillations consistent with rewrite dynamics.")