#!/usr/bin/env python3
"""
Test C6 — Two-Mass Curvature Interaction (Emergent Gravitational Coupling)
------------------------------------------------------------------------
Goal:
Simulate two localized curvature wells that attract and merge under
rewrite-based curvature evolution — demonstrating emergent gravity-like coupling.

Artifacts:
  - PAEV_TestC6_TwoMass_Interaction.png
  - PAEV_TestC6_TwoMass_Animation.gif
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# -------------------- setup lattice --------------------
N = 101
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
R = np.stack([X, Y], axis=-1)

# two Gaussian masses
r1, r2 = np.array([-0.4, 0]), np.array([0.4, 0])
sigma = 0.15
M = np.exp(-np.sum((R - r1)**2, axis=-1)/(2*sigma**2)) \
  + np.exp(-np.sum((R - r2)**2, axis=-1)/(2*sigma**2))
M /= M.max()

# initial curvature proportional to mass
kappa = M.copy()

# parameters
eta = 0.1      # feedback rate
alpha = 0.5    # diffusion factor (smoothing)
steps = 100
save_every = 5

# precompute Laplacian kernel
LAP = np.array([[0,1,0],[1,-4,1],[0,1,0]])

def laplacian(Z):
    from scipy.signal import convolve2d
    return convolve2d(Z, LAP, mode='same', boundary='symm')

# -------------------- evolution loop --------------------
frames = []
for t in range(steps):
    # rewrite influence = smoothed curvature (like metric diffusion)
    D_rw = np.sqrt((laplacian(kappa)**2))
    # feedback: curvature pulled toward local mass + rewrite deformation
    kappa += eta * (M - alpha*D_rw)
    kappa = np.clip(kappa, 0, None)
    kappa /= kappa.max() + 1e-12
    if t % save_every == 0:
        frames.append(kappa.copy())

# -------------------- visualization --------------------
fig, ax = plt.subplots(figsize=(5,5))
im = ax.imshow(frames[0], cmap='inferno', vmin=0, vmax=1)
ax.set_title("Test C6 — Two-Mass Curvature Interaction")
ax.axis('off')

def update(frame):
    im.set_data(frame)
    return [im]

ani = FuncAnimation(fig, update, frames=frames, interval=100, blit=True)
ani.save("PAEV_TestC6_TwoMass_Animation.gif", writer="pillow", fps=10)
plt.savefig("PAEV_TestC6_TwoMass_Interaction.png", dpi=180)

print("✅ Saved plot to: PAEV_TestC6_TwoMass_Interaction.png")
print("✅ Saved animation to: PAEV_TestC6_TwoMass_Animation.gif")
print(f"=== Test C6 — complete: N={N}, steps={steps}, η={eta}, α={alpha} ===")