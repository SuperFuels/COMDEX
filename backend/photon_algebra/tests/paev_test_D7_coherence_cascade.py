"""
PAEV Test D7 — Quantum Coherence Cascade
---------------------------------------
Objective:
  • Test curvature–phase coupling between multiple field modes ψ₁, ψ₂.
  • Detect synchronized curvature oscillations ("field resonance coherence").
  • Analyze cross-mode entanglement and coherence transfer.

Expected Outcome:
  • Phase–energy synchronization across ψ₁ and ψ₂.
  • Stable curvature energy exchange (resonant oscillations).
  • Emergent “coherence cascade” (curvature → phase → cross-mode).
"""

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from pathlib import Path

# -----------------------------------
# 1. Simulation parameters
# -----------------------------------
N = 121               # Grid size
steps = 600           # Time steps
dt = 0.05             # Time increment
gamma_couple = 0.04   # Coupling strength between ψ₁ and ψ₂
kappa_rate = 0.002    # Curvature evolution rate

out_dir = Path("/workspaces/COMDEX")
out_dir.mkdir(parents=True, exist_ok=True)

# -----------------------------------
# 2. Initialization
# -----------------------------------
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# Two initial Gaussian modes (offset to create phase interaction)
psi1 = np.exp(-((X + 0.3)**2 + Y**2) * 8) * np.exp(1j * np.pi * X)
psi2 = np.exp(-((X - 0.3)**2 + Y**2) * 8) * np.exp(-1j * np.pi * X)

# Curvature field — starts small
kappa = 0.1 * np.exp(-5 * (X**2 + Y**2))

# Arrays for energy tracking
energy_trace = []
coherence_trace = []
cross_coherence_trace = []
frames = []

# -----------------------------------
# 3. Evolution
# -----------------------------------
def laplacian(f):
    return np.roll(f, 1, axis=0) + np.roll(f, -1, axis=0) + np.roll(f, 1, axis=1) + np.roll(f, -1, axis=1) - 4 * f

for t in range(steps):
    # Compute Laplacians
    lap1 = laplacian(psi1)
    lap2 = laplacian(psi2)

    # Phase-coupled evolution equations
    dpsi1 = 1j * (lap1 - kappa * psi1) + gamma_couple * (psi2 - psi1)
    dpsi2 = 1j * (lap2 - kappa * psi2) + gamma_couple * (psi1 - psi2)

    psi1 += dt * dpsi1
    psi2 += dt * dpsi2

    # Normalize to keep amplitude bounded
    psi1 /= (np.abs(psi1).max() + 1e-12)
    psi2 /= (np.abs(psi2).max() + 1e-12)

    # Curvature evolution — responds to phase gradients
    grad_theta1 = np.angle(psi1)
    grad_theta2 = np.angle(psi2)
    d_kappa = kappa_rate * (laplacian(grad_theta1 + grad_theta2))
    kappa += dt * d_kappa

    # Energy metrics
    energy = np.mean(np.abs(laplacian(np.angle(psi1 + psi2)))**2)
    coherence = np.mean(np.abs(psi1)) + np.mean(np.abs(psi2))
    cross_coherence = np.mean(np.abs(np.conj(psi1) * psi2))

    energy_trace.append(energy)
    coherence_trace.append(coherence)
    cross_coherence_trace.append(cross_coherence)

    # Visualization frames
    if t % 20 == 0:
        fig, ax = plt.subplots(figsize=(6,6))
        ax.imshow(np.angle(psi1 + psi2), cmap="twilight", extent=[-1,1,-1,1])
        ax.set_title(f"Test D7 — Quantum Coherence Cascade\nStep {t}")
        ax.axis("off")
        fig.canvas.draw()
        img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
        frames.append(img)
        plt.close(fig)

    if t % 50 == 0:
        print(f"Step {t:04d} — Energy={energy:.4f}, ⟨|ψ|⟩={coherence:.4f}, Cross={cross_coherence:.4f}")

# -----------------------------------
# 4. Save results
# -----------------------------------
imageio.mimsave(out_dir / "PAEV_TestD7_CoherenceCascade.gif", frames, fps=10)
print(f"✅ Saved animation to: {out_dir / 'PAEV_TestD7_CoherenceCascade.gif'}")

# Energy plot
plt.figure()
plt.plot(energy_trace, color="blue")
plt.title("Test D7 — Energy Evolution (Quantum Coherence Cascade)")
plt.xlabel("Time step")
plt.ylabel("Mean curvature energy ⟨|∇θ|²⟩")
plt.tight_layout()
plt.savefig(out_dir / "PAEV_TestD7_CoherenceCascade_Energy.png")
plt.close()
print(f"✅ Saved file: {out_dir / 'PAEV_TestD7_CoherenceCascade_Energy.png'}")

# Coherence plots
plt.figure()
plt.plot(coherence_trace, label="Total ⟨|ψ|⟩", color="purple")
plt.plot(cross_coherence_trace, label="Cross-mode coherence", color="orange")
plt.title("Test D7 — Mode Coherence Evolution")
plt.xlabel("Time step")
plt.ylabel("Coherence amplitude")
plt.legend()
plt.tight_layout()
plt.savefig(out_dir / "PAEV_TestD7_CoherenceCascade_Coherence.png")
plt.close()
print(f"✅ Saved file: {out_dir / 'PAEV_TestD7_CoherenceCascade_Coherence.png'}")

print("\n=== Test D7 — Quantum Coherence Cascade Complete ===")
print(f"⟨Energy⟩ = {np.mean(energy_trace):.4f}")
print(f"⟨|ψ|⟩ = {np.mean(coherence_trace):.4f}")
print(f"⟨Cross⟩ = {np.mean(cross_coherence_trace):.4f}")
print(f"Files saved to {out_dir}")