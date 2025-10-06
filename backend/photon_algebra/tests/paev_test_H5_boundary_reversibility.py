"""
PAEV Test H5 — Boundary Condition Reversibility
------------------------------------------------
Goal:
    Verify that the photon-algebraic field equations (ψ–κ system)
    remain time-reversible and energy-consistent when boundary
    conditions are inverted (t → -t).

Significance:
    Time-symmetric reversibility under the unified algebra implies
    conservation across temporal reflection — a hallmark of
    a physically complete algebraic model (precursor to TOE H-layer).
"""

import numpy as np
import matplotlib.pyplot as plt
import os

# -------------------------------------------------------------------
# Inline 2D Laplacian
# -------------------------------------------------------------------
def laplacian_2d(field):
    """Discrete 2D Laplacian operator."""
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4 * field
    )

# -------------------------------------------------------------------
# Simulation Parameters
# -------------------------------------------------------------------
N = 128
steps = 600
dt = 0.01
gamma = 0.015

# Initialize fields as complex128
x = np.linspace(-2, 2, N)
X, Y = np.meshgrid(x, x)

psi = np.exp(-(X**2 + Y**2)) * np.exp(1j * 0.2 * X)
psi = psi.astype(np.complex128)

kappa = 0.5 * np.exp(-(X**2 + Y**2))
kappa = kappa.astype(np.complex128)

energy_trace = []
entropy_trace = []

# -------------------------------------------------------------------
# Forward evolution
# -------------------------------------------------------------------
for step in range(steps):
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)

    psi_t = (1j * dt) * (lap_psi - kappa * psi)
    kappa_t = dt * (0.05 * lap_kappa + 0.1 * np.real(psi) - 0.02 * kappa)

    psi += gamma * psi_t
    kappa += gamma * kappa_t

    energy = np.mean(np.abs(psi) ** 2 + np.abs(kappa) ** 2)
    entropy = -np.sum(np.abs(psi) ** 2 * np.log(np.abs(psi) ** 2 + 1e-12))
    energy_trace.append(energy)
    entropy_trace.append(entropy)

psi_forward = np.copy(psi)
kappa_forward = np.copy(kappa)

# -------------------------------------------------------------------
# Reverse evolution (t → -t)
# -------------------------------------------------------------------
for step in range(steps):
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)

    psi_t = (-1j * dt) * (lap_psi - kappa * psi)
    kappa_t = -dt * (0.05 * lap_kappa + 0.1 * np.real(psi) - 0.02 * kappa)

    psi += gamma * psi_t
    kappa += gamma * kappa_t

# -------------------------------------------------------------------
# Compare fields
# -------------------------------------------------------------------
rev_error = np.mean(np.abs(psi - psi_forward)) + np.mean(np.abs(kappa - kappa_forward))
energy_drift = np.abs(energy_trace[-1] - energy_trace[0])
entropy_drift = np.abs(entropy_trace[-1] - entropy_trace[0])

# -------------------------------------------------------------------
# Plots
# -------------------------------------------------------------------
out1 = "PAEV_TestH5_EnergyDrift.png"
out2 = "PAEV_TestH5_EntropyEvolution.png"
out3 = "PAEV_TestH5_ReversibilityError.png"

plt.figure(figsize=(6, 4))
plt.plot(energy_trace, label="Energy ⟨E⟩")
plt.title("H5 — Energy Drift Over Time")
plt.xlabel("Step")
plt.ylabel("Energy")
plt.legend()
plt.tight_layout()
plt.savefig(out1)

plt.figure(figsize=(6, 4))
plt.plot(entropy_trace, color='orange', label="Spectral Entropy")
plt.title("H5 — Entropy Evolution (ψ Field)")
plt.xlabel("Step")
plt.ylabel("Entropy")
plt.legend()
plt.tight_layout()
plt.savefig(out2)

plt.figure(figsize=(5, 4))
plt.imshow(np.abs(psi - psi_forward), cmap="inferno")
plt.colorbar(label="|Δψ| (Reversibility Error)")
plt.title("H5 — Final Reversibility Error Field")
plt.tight_layout()
plt.savefig(out3)

# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------
print("\n=== Test H5 — Boundary Condition Reversibility Complete ===")
print(f"⟨E⟩ drift      = {energy_drift:.6e}")
print(f"⟨S⟩ drift      = {entropy_drift:.6e}")
print(f"Reversibility error = {rev_error:.6e}")
print("All output files saved:")
for p in [out1, out2, out3]:
    print(f" - {os.path.abspath(p)}")
print("----------------------------------------------------------")