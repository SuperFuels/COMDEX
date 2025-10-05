#!/usr/bin/env python3
"""
Test D5 — Vortex Pair Annihilation & Recombination

Goal
- Create a vortex–antivortex pair in a 2D phase field θ(x,y).
- Evolve θ with a diffusion-like wave equation + weak “drive” and damping.
- Track total topological charge Q(t) and count of vortices/antivortices.
- Show: (i) annihilation (Q conserved; local ±1 charges cancel); and
        (ii) possible recombination under weak noise/drive.
Artifacts
- PAEV_TestD5_Vortex_ChargeTrace.png
- PAEV_TestD5_Vortex_Phase.png
- PAEV_TestD5_Vortex_Vorticity.png
- PAEV_TestD5_Vortex_Energy.png
- PAEV_TestD5_Vortex.gif
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import imageio.v2 as imageio
from pathlib import Path

# ------------------ helpers ------------------

def wrap(ang):
    """Wrap angle to (-pi, pi]."""
    return (ang + np.pi) % (2*np.pi) - np.pi

def laplacian(Z):
    return (
        -4 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

def grad_theta(theta):
    """Wrapped gradient of phase field."""
    dtx = wrap(np.roll(theta, -1, 1) - theta)  # x-forward
    dty = wrap(np.roll(theta, -1, 0) - theta)  # y-forward
    return dtx, dty

def vorticity(theta):
    """
    Lattice ‘plaquette’ winding number density in integers.
    Sum wrapped phase differences around each unit square.
    """
    dtx, dty = grad_theta(theta)
    # corner sums around plaquette
    a = dtx
    b = np.roll(dty, -1, 1)
    c = -np.roll(dtx, -1, 0)
    d = -dty
    wind = wrap(a + b + c + d) / (2*np.pi)
    # round tiny floating errors to nearest integer in {-1,0,1}
    return np.rint(wind).astype(int)

def total_charge(theta):
    return int(np.sum(vorticity(theta)))

def count_vortices(theta):
    w = vorticity(theta)
    return int(np.sum(w == 1)), int(np.sum(w == -1))

def energy(theta):
    """Simple XY-model like energy ~ |∇θ|^2."""
    dtx, dty = grad_theta(theta)
    return float(np.sum(dtx**2 + dty**2))

def make_ring_mask(N, center, r, width=2.0):
    Y, X = np.indices((N, N))
    rr = np.sqrt((X-center[1])**2 + (Y-center[0])**2)
    return np.exp(-0.5*((rr-r)/width)**2)

# ------------------ initialization ------------------

def seed_vortex_pair(N=121, sep=30, core=2.5):
    """
    Make a vortex (+1) and antivortex (-1) centered horizontally.
    """
    cy = N//2
    cx1 = N//2 - sep//2
    cx2 = N//2 + sep//2

    Y, X = np.indices((N, N))
    ang1 = np.arctan2(Y-cy, X-cx1)
    ang2 = np.arctan2(Y-cy, X-cx2)

    theta = wrap(ang1 - ang2)  # +1 at left, -1 at right
    # Soften cores a bit to avoid huge gradients
    r1 = np.sqrt((X-cx1)**2 + (Y-cy)**2)
    r2 = np.sqrt((X-cx2)**2 + (Y-cy)**2)
    soft = np.tanh(r1/core) * np.tanh(r2/core)
    return wrap(theta * soft)

# ------------------ dynamics ------------------

def step(theta, dt, kappa=0.35, gamma=0.03, drive_amp=0.04, noise=1e-3, t=0):
    """
    Semi-discrete update:
      θ_{t+dt} = θ + dt*( κ∇²θ - γθ + drive + noise )
    drive = weak ring driver that can promote recombination after annihilation.
    """
    N = theta.shape[0]
    # weak ring driver pulsing slowly
    ring = make_ring_mask(N, center=(N//2, N//2), r=N*0.22, width=3.0)
    drive = drive_amp * np.sin(2*np.pi*(0.005*t)) * ring

    dtheta = kappa * laplacian(theta) - gamma * theta + drive
    if noise > 0.0:
        dtheta += noise * np.random.randn(*theta.shape)

    th_next = wrap(theta + dt * dtheta)
    return th_next

# ------------------ main experiment ------------------

def run(
    N=121, steps=400, dt=0.02, kappa=0.35, gamma=0.03,
    drive_amp=0.04, noise=8e-4, save_every=5
):
    theta = seed_vortex_pair(N=N, sep=34, core=2.2)

    charges = []
    nv_list, na_list = [], []
    energy_trace = []

    frames = []
    cmap = cm.inferno

    for t in range(steps):
        if t % save_every == 0:
            # render phase (nice for seeing annihilation line)
            fig, ax = plt.subplots(figsize=(5,5))
            im = ax.imshow(theta, cmap=cmap, vmin=-np.pi, vmax=np.pi)
            ax.set_title("Test D5 — Vortex Pair (phase)")
            ax.set_xticks([]); ax.set_yticks([])
            plt.tight_layout()
            # save frame to memory for gif
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
            frames.append(img)
            plt.close(fig)

        # diagnostics
        charges.append(total_charge(theta))
        nv, na = count_vortices(theta)
        nv_list.append(nv); na_list.append(na)
        energy_trace.append(energy(theta))

        # evolve
        theta = step(theta, dt, kappa, gamma, drive_amp, noise, t)

    return theta, np.array(charges), np.array(nv_list), np.array(na_list), np.array(energy_trace), frames

# ------------------ plotting ------------------

def save_artifacts(theta, charges, nv, na, energy_trace, frames):
    out_gif = "PAEV_TestD5_Vortex.gif"
    out_phase = "PAEV_TestD5_Vortex_Phase.png"
    out_vort = "PAEV_TestD5_Vortex_Vorticity.png"
    out_charge = "PAEV_TestD5_Vortex_ChargeTrace.png"
    out_energy = "PAEV_TestD5_Vortex_Energy.png"

    # GIF
    imageio.mimsave(out_gif, frames, duration=0.06)
    print(f"✅ Saved animation to: {out_gif}")

    # Final phase
    plt.figure(figsize=(5.2,5.2))
    plt.imshow(theta, cmap="twilight", vmin=-np.pi, vmax=np.pi)
    plt.colorbar(label="phase θ (rad)")
    plt.title("Test D5 — Final Phase θ(x,y)")
    plt.xticks([]); plt.yticks([])
    plt.tight_layout()
    plt.savefig(out_phase, dpi=160)
    plt.close()
    print(f"✅ Saved phase image to: {out_phase}")

    # Vorticity map
    W = vorticity(theta)
    plt.figure(figsize=(5.2,5.2))
    plt.imshow(W, cmap="bwr", vmin=-1, vmax=1)
    plt.colorbar(label="winding (±1)")
    plt.title("Test D5 — Final Vorticity (winding)")
    plt.xticks([]); plt.yticks([])
    plt.tight_layout()
    plt.savefig(out_vort, dpi=160)
    plt.close()
    print(f"✅ Saved vorticity image to: {out_vort}")

    # Charge / counts trace
    t = np.arange(len(charges))
    fig, ax = plt.subplots(figsize=(7.5,4.2))
    ax.plot(t, charges, 'k-', label="Total charge Q(t)")
    ax.plot(t, nv, 'g--', label="# vortices (+1)")
    ax.plot(t, na, 'r--', label="# antivortices (-1)")
    ax.set_xlabel("Time step")
    ax.set_ylabel("Count / charge")
    ax.set_title("Test D5 — Vortex Annihilation & Recombination Trace")
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_charge, dpi=160)
    plt.close()
    print(f"✅ Saved charge/count trace to: {out_charge}")

    # Energy trace
    plt.figure(figsize=(7.5,4.2))
    plt.plot(energy_trace)
    plt.xlabel("Time step")
    plt.ylabel("Total curvature energy (~|∇θ|²)")
    plt.title("Test D5 — Energy Evolution")
    plt.tight_layout()
    plt.savefig(out_energy, dpi=160)
    plt.close()
    print(f"✅ Saved energy plot to: {out_energy}")

# ------------------ entry ------------------

if __name__ == "__main__":
    np.random.seed(2)
    theta, charges, nv, na, energy_trace, frames = run(
        N=121, steps=400, dt=0.02,
        kappa=0.35, gamma=0.03,
        drive_amp=0.04, noise=8e-4, save_every=5
    )

    Q0, Qf = charges[0], charges[-1]
    annihilated = (np.min(nv + na) == 0) or (np.any((nv+na)[:-1] > (nv+na)[1:]))
    recomb_possible = np.any((nv+na)[1:] > (nv+na)[:-1])  # count rises again

    print("=== Test D5 — Vortex Pair Annihilation & Recombination ===")
    print(f"Initial total charge Q0 = {Q0}")
    print(f"Final   total charge Qf = {Qf}")
    print(f"Charge conserved? {'YES' if Q0 == Qf else 'NO'}")
    print(f"Annihilation observed? {'YES' if annihilated else 'NO'}")
    print(f"Recombination hints? {'YES' if recomb_possible else 'NO'}")

    save_artifacts(theta, charges, nv, na, energy_trace, frames)