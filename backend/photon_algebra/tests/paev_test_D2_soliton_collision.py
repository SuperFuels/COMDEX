import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Normalization utility ---
def normalize(x):
    return (x - np.min(x)) / (np.ptp(x) + 1e-12)

# --- Simulation parameters ---
N = 121
steps = 400
dx = 1.0
dt = 0.1
c = 1.0      # propagation speed
gamma = 0.005  # damping term (energy loss control)
eta = 0.15     # nonlinearity coupling

# --- Spatial grid ---
x = np.arange(N)
y = np.arange(N)
X, Y = np.meshgrid(x, y)
cx1, cx2 = 45, 75
cy = 60
sigma = 6.0

# --- Initial curvature field: two solitons ---
kappa = np.exp(-((X - cx1)**2 + (Y - cy)**2) / (2 * sigma**2)) \
      + np.exp(-((X - cx2)**2 + (Y - cy)**2) / (2 * sigma**2))
kappa = normalize(kappa) * 2.0 - 1.0
v = np.zeros_like(kappa)  # velocity field

# --- Storage for energy ---
energy = []

# --- Helper: Laplacian ---
def laplacian(Z):
    return (
        np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0) +
        np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1) - 4 * Z
    ) / dx**2

# --- Time evolution loop ---
frames = []
for t in range(steps):
    lap = laplacian(kappa)
    acc = c**2 * lap - eta * kappa**3 - gamma * v
    v += dt * acc
    kappa += dt * v

    if t % 5 == 0:
        frames.append(normalize(kappa).copy())

    energy.append(np.sum(kappa**2))

# --- Visualization ---
fig, ax = plt.subplots()
im = ax.imshow(frames[0], cmap="inferno", animated=True)
plt.title("Test D2 — Soliton Collision Dynamics")

def update(frame):
    im.set_array(frame)
    return [im]

ani = FuncAnimation(fig, update, frames=frames, interval=40, blit=True)
ani.save("PAEV_TestD2_SolitonCollision.gif", fps=20)
print("✅ Saved animation to: PAEV_TestD2_SolitonCollision.gif")

# --- Energy plot ---
plt.figure()
plt.plot(energy, color="blue")
plt.xlabel("Time step")
plt.ylabel("Total curvature energy (κ²)")
plt.title("Test D2 — Total Energy Evolution (Collision Stability)")
plt.tight_layout()
plt.savefig("PAEV_TestD2_SolitonCollision_Energy.png", dpi=160)
print("✅ Saved energy plot to: PAEV_TestD2_SolitonCollision_Energy.png")

# --- Print summary ---
e_init = energy[0]
e_final = energy[-1]
deltaE = e_final - e_init
print("\n=== Test D2 — Soliton Collision Complete ===")
print(f"Energy initial={e_init:.3e}, final={e_final:.3e}, ΔE={deltaE:.3e}")
print(f"Frames: {len(frames)}, N={N}, dt={dt}, steps={steps}")