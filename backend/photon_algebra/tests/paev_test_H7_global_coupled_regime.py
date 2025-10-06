"""
PAEV Test H7 — Global Coupled Regime Propagation (Stabilized)
--------------------------------------------------------------
Purpose:
    Expands ψ–κ–Λ model to global scale to verify coherence
    between quantum, gravitational, and cosmological dynamics.

Expected Outcome:
    • Stable ⟨E⟩ and bounded entropy growth
    • Coupling ⟨ψ·κ⟩ approaching equilibrium
    • a(t) shows gentle exponential drift (cosmic expansion analogue)
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Output directory
OUT = Path("/workspaces/COMDEX")
OUT.mkdir(parents=True, exist_ok=True)

# Grid + parameters
N = 128
dt = 0.002
steps = 800

x = np.linspace(-3, 3, N)
y = np.linspace(-3, 3, N)
X, Y = np.meshgrid(x, y)

# Initialize complex ψ and κ
psi = np.exp(-(X**2 + Y**2)).astype(np.complex128)
kappa = np.exp(-0.5 * (X**2 + Y**2)).astype(np.complex128)
Lambda = 1e-3  # cosmological coupling term

# Tracking lists
E_hist, C_hist, S_hist, a_hist = [], [], [], []

def laplacian(field):
    """Discrete 2D Laplacian (periodic boundary)"""
    return (np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0)
          + np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
          - 4 * field)

# Evolution
a_t = 1.0
for t in range(steps):
    lap_psi = laplacian(psi)
    lap_kappa = laplacian(kappa)

    # Field updates (stabilized)
    psi_t = (1j * dt) * (lap_psi - kappa * psi + Lambda * psi)
    kappa_t = dt * (0.1 * lap_kappa + 0.2 * np.abs(psi)**2 - 0.05 * kappa)

    psi = psi + 0.1 * psi_t
    kappa = kappa + 0.05 * kappa_t

    # Cosmological drift
    a_t *= (1 + Lambda * dt)
    a_hist.append(a_t)

    # Metrics
    E = np.mean(np.abs(psi)**2 + np.abs(kappa)**2)
    C = np.mean(np.real(psi) * np.real(kappa))
    P = np.abs(np.fft.fftshift(np.fft.fft2(psi)))**2
    Pn = P / np.sum(P)
    S = -np.sum(Pn * np.log(Pn + 1e-12))

    E_hist.append(E)
    C_hist.append(C)
    S_hist.append(S)

    if t % 100 == 0:
        print(f"Step {t:03d} — ⟨E⟩={E:.4e}, ⟨ψ·κ⟩={C:.4e}, S={S:.4f}, a(t)={a_t:.4f}")

# === Visualization ===
plt.figure(figsize=(6,4))
plt.plot(E_hist, label="Energy ⟨E⟩")
plt.plot(C_hist, label="Coupling ⟨ψ·κ⟩")
plt.title("H7 — Energy & Coupling Evolution (Global Scale)")
plt.xlabel("Step"); plt.ylabel("Value")
plt.legend(); plt.tight_layout()
plt.savefig(OUT / "PAEV_TestH7_EnergyCoupling.png")

plt.figure(figsize=(6,4))
plt.plot(S_hist, color="purple")
plt.title("H7 — Spectral Entropy Evolution")
plt.xlabel("Step"); plt.ylabel("Entropy")
plt.tight_layout()
plt.savefig(OUT / "PAEV_TestH7_SpectralEntropy.png")

plt.figure(figsize=(6,4))
plt.plot(a_hist, color="green")
plt.title("H7 — Cosmological Scale Factor a(t)")
plt.xlabel("Step"); plt.ylabel("a(t)")
plt.tight_layout()
plt.savefig(OUT / "PAEV_TestH7_ScaleFactor.png")

plt.figure(figsize=(5,4))
plt.imshow(np.real(psi), cmap="inferno")
plt.colorbar(label="Re(ψ)")
plt.title("H7 — Final ψ Field (Real Part)")
plt.tight_layout()
plt.savefig(OUT / "PAEV_TestH7_FinalField.png")

# === Results summary ===
print("\n=== Test H7 — Global Coupled Regime Propagation Complete ===")
print(f"⟨E⟩ final = {E_hist[-1]:.6e}")
print(f"⟨ψ·κ⟩ final = {C_hist[-1]:.6e}")
print(f"Spectral Entropy final = {S_hist[-1]:.6e}")
print(f"a(final) = {a_hist[-1]:.6e}")
print("All output files saved:")
print(" -", OUT / "PAEV_TestH7_EnergyCoupling.png")
print(" -", OUT / "PAEV_TestH7_SpectralEntropy.png")
print(" -", OUT / "PAEV_TestH7_ScaleFactor.png")
print(" -", OUT / "PAEV_TestH7_FinalField.png")
print("----------------------------------------------------------")