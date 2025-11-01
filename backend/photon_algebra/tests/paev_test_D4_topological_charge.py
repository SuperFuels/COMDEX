#!/usr/bin/env python3
"""
Test D4 - Topological Charge Conservation (vortex defects)

We evolve a complex field Ψ = A e^{iθ} under a damped wave/Schrödinger-like
update that keeps phase dynamics, seed two opposite-charge vortices, and
track the integer winding number (topological charge) over time.

Artifacts:
- PAEV_TestD4_Topology_Phase.png        (final phase field)
- PAEV_TestD4_Topology_Vorticity.png    (final integer vorticity map)
- PAEV_TestD4_Topology_ChargeTrace.png  (total charge vs time)
- PAEV_TestD4_Topology.gif              (phase evolution)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# -------------------- helpers --------------------
def laplacian(Z):
    return (
        -4*Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

def normalize_phase_phaseunwrap(psi):
    # unit-modulus complex; keep amplitude ~1, focus on phase
    mag = np.abs(psi)
    mag[mag == 0] = 1.0
    return psi / mag

def phase(Z):
    return np.angle(Z)

def discrete_winding(theta):
    """
    Compute integer vorticity on each plaquette by summing wrapped
    phase differences around elementary squares (lattice curl of ∇θ).
    Returns an (N-1)x(N-1) array of integer charges.
    """
    # phase diffs with wrapping to (-pi, pi]
    def wrap(d):
        d = (d + np.pi) % (2*np.pi) - np.pi
        return d

    dθx = wrap(np.diff(theta, axis=1))        # N x (N-1)
    dθy = wrap(np.diff(theta, axis=0))        # (N-1) x N

    # circulation around each cell:
    # top edge: dθx[0:-1, :]
    # right edge: dθy[:,1:]
    # bottom edge: -dθx[1:, :]
    # left edge: -dθy[:,0:-1]
    circ = (
        dθx[:-1, :] +
        dθy[:, 1:] -
        dθx[1:, :] -
        dθy[:, :-1]
    )
    # integer charge per plaquette = round(circ / 2π)
    Q = np.rint(circ / (2*np.pi)).astype(int)
    return Q

# -------------------- setup --------------------
N = 121
x = np.linspace(-3.0, 3.0, N)
y = np.linspace(-3.0, 3.0, N)
X, Y = np.meshgrid(x, y)

# seed two vortices: +1 at (-1,0), -1 at (+1,0)
def vortex_phase(x0, y0, charge=1):
    return charge * np.arctan2(Y - y0, X - x0)

theta0 = vortex_phase(-1.0, 0.0, +1) + vortex_phase(+1.0, 0.0, -1)
A0 = np.exp(-0.5 * (X**2 + Y**2)) * 0.2 + 1.0  # gentle amplitude bump
psi = A0 * np.exp(1j * theta0)

# dynamics parameters (stable, damped phase flow)
dt = 0.02
kappa = 0.35       # propagation stiffness
gamma = 0.03       # damping
steps = 400
frame_every = 5

# -------------------- evolve & record --------------------
charges = []
frames = []
for t in range(steps):
    # damped wave/Schrödinger-like step on complex field
    psi = psi + dt * (1j * kappa * laplacian(psi) - gamma * (psi - psi/np.abs(psi)))
    psi = normalize_phase_phaseunwrap(psi)

    if t % frame_every == 0 or t == steps-1:
        th = phase(psi)
        Q = discrete_winding(th)
        total_Q = int(np.sum(Q))
        charges.append((t, total_Q))
        frames.append(th.copy())

# -------------------- outputs --------------------
# Charge trace
ts = [t for t, _ in charges]
Qs = [q for _, q in charges]
plt.figure(figsize=(6.6,4.2))
plt.plot(ts, Qs, '-o', lw=2, ms=3)
plt.xlabel("Time step")
plt.ylabel("Total topological charge")
plt.title("Test D4 - Topological Charge Conservation")
plt.grid(alpha=0.25)
plt.tight_layout()
plt.savefig("PAEV_TestD4_Topology_ChargeTrace.png", dpi=160)

# Final phase & vorticity maps
theta_f = frames[-1]
Qf = discrete_winding(theta_f)

plt.figure(figsize=(5.8,5.4))
plt.imshow(theta_f, cmap="twilight", origin="lower")
plt.title("Test D4 - Final Phase θ(x,y)")
plt.colorbar(label="phase (rad)")
plt.tight_layout()
plt.savefig("PAEV_TestD4_Topology_Phase.png", dpi=160)

plt.figure(figsize=(5.8,5.4))
plt.imshow(Qf, cmap="bwr", origin="lower", vmin=-1, vmax=1)
plt.title("Test D4 - Integer Vorticity (winding)")
plt.colorbar(label="charge per cell")
plt.tight_layout()
plt.savefig("PAEV_TestD4_Topology_Vorticity.png", dpi=160)

# Animation of phase
fig, ax = plt.subplots(figsize=(5.8,5.4))
im = ax.imshow(frames[0], cmap="twilight", origin="lower", animated=True)
ax.set_title("Test D4 - Phase evolution")
ax.set_axis_off()

def update(i):
    im.set_array(frames[i])
    return [im]

ani = animation.FuncAnimation(fig, update, frames=len(frames), blit=True, interval=60)
try:
    ani.save("PAEV_TestD4_Topology.gif", writer="pillow", dpi=140)
except Exception:
    ani.save("PAEV_TestD4_Topology.gif", dpi=140)

# Print summary
print("=== Test D4 - Topological Charge Conservation ===")
print(f"Grid {N}x{N}, steps={steps}, dt={dt}, kappa={kappa}, gamma={gamma}")
print(f"Initial total charge Q0 = {Qs[0]}")
print(f"Final   total charge Qf = {Qs[-1]}")
print(f"Conserved? {'YES' if Qs[0]==Qs[-1] else 'NO'}")
print("Artifacts:")
print(" - PAEV_TestD4_Topology_ChargeTrace.png")
print(" - PAEV_TestD4_Topology_Phase.png")
print(" - PAEV_TestD4_Topology_Vorticity.png")
print(" - PAEV_TestD4_Topology.gif")