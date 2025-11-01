"""
Test D6 - Quantum Vortex Lattice and Emergent Order
---------------------------------------------------
This simulation explores spontaneous formation of quantized vortex lattices
in the photon-algebra curvature phase field. Analogous to Abrikosov lattices
in superconductors or vortex order in rotating BECs.
"""

import numpy as np
import matplotlib.pyplot as plt
import imageio
from matplotlib.colors import hsv_to_rgb

# --- Parameters ---
N = 181            # grid size
steps = 600        # time evolution steps
dt = 0.05          # time step
kappa = 0.25       # coupling strength
gamma = 0.02       # damping
save_every = 10    # save frame frequency

# --- Spatial grid ---
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
r = np.sqrt(X**2 + Y**2)
phi = np.arctan2(Y, X)

# --- Initial phase field (rotational symmetry + perturbation) ---
n = 3  # base winding
theta = n * phi + 0.1 * np.random.randn(N, N)
psi = np.exp(1j * theta)

# --- Utility functions ---
def laplacian(Z):
    return (
        -4 * Z
        + np.roll(Z, 1, 0)
        + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1)
        + np.roll(Z, -1, 1)
    )

def normalize(Z):
    return (Z - Z.min()) / (np.ptp(Z) + 1e-12)

# --- Simulation core ---
frames = []
energy_trace = []
coherence_trace = []

for t in range(steps):
    lap = laplacian(psi)
    dpsi = kappa * lap - gamma * (np.abs(psi)**2 - 1) * psi
    psi += dt * dpsi
    psi /= np.abs(psi) + 1e-12  # normalize magnitude
    theta = np.angle(psi)

    # Compute energy
    gradx, grady = np.gradient(theta)
    energy = np.mean(gradx**2 + grady**2)
    energy_trace.append(energy)

    # Compute coherence
    coherence = np.abs(np.mean(np.exp(1j * theta)))
    coherence_trace.append(coherence)

    # Save frame every few steps
    if t % save_every == 0:
        hue = (theta + np.pi) / (2 * np.pi)
        sat = np.ones_like(hue)
        val = normalize(np.abs(psi))
        rgb = hsv_to_rgb(np.stack([hue, sat, val], axis=-1))
        frames.append((rgb * 255).astype(np.uint8))
        print(f"Step {t:04d} - Energy={energy:.4f}, Coherence={coherence:.4f}")

# --- Save outputs ---
print("\n=== Test D6 - Vortex Lattice Formation ===")

import os

# --- Safe save helper ---
def safe_savefig(filename, *args, **kwargs):
    """Ensure consistent path and report absolute location."""
    outpath = os.path.abspath(filename)
    plt.savefig(outpath, *args, **kwargs)
    plt.close()
    if os.path.exists(outpath):
        print(f"✅ Saved file: {outpath}")
    else:
        print(f"⚠️ Warning: File not found after save attempt: {outpath}")

# --- Animation save ---
gif_path = os.path.abspath("PAEV_TestD6_VortexLattice.gif")
imageio.mimsave(gif_path, frames, fps=10)
print(f"✅ Saved animation to: {gif_path}")

# --- Final phase plot ---
plt.figure(figsize=(6, 6))
plt.imshow(np.angle(psi), cmap="twilight", extent=[-1, 1, -1, 1])
plt.title("Test D6 - Final Phase Field θ(x,y)")
plt.colorbar(label="phase (rad)")
plt.tight_layout()
safe_savefig("PAEV_TestD6_VortexLattice_Phase.png")

# --- Energy evolution ---
plt.figure()
plt.plot(energy_trace, color="blue")
plt.title("Test D6 - Energy Evolution (Vortex Lattice Formation)")
plt.xlabel("Time step")
plt.ylabel("Mean curvature energy ⟨|∇θ|2⟩")
plt.tight_layout()
safe_savefig("PAEV_TestD6_VortexLattice_Energy.png")

# --- Coherence evolution ---
plt.figure()
plt.plot(coherence_trace, color="purple")
plt.title("Test D6 - Order Parameter Evolution (ψ coherence)")
plt.xlabel("Time step")
plt.ylabel("⟨|ψ|⟩ coherence")
plt.tight_layout()
safe_savefig("PAEV_TestD6_VortexLattice_OrderParameter.png")

# --- Summary ---
mean_E = np.mean(energy_trace)
mean_coh = np.mean(coherence_trace)
print("\nFinal metrics:")
print(f"  ⟨E⟩ = {mean_E:.4f}")
print(f"  ⟨|ψ|⟩ = {mean_coh:.4f}")
print("=== Test D6 complete ===")

# Explicit reminder
print("\n📁 All outputs saved in:")
print(f"   {os.getcwd()}")
print("   (Absolute paths printed above confirm accessibility.)")