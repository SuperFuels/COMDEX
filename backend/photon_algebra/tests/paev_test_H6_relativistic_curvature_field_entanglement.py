import numpy as np
import matplotlib.pyplot as plt
import os

# --- Simulation Parameters ---
N = 128
dx = 1.0
dt = 0.02
steps = 600
output_dir = "/workspaces/COMDEX"

# --- Initialize Fields ---
x, y = np.meshgrid(np.linspace(-3, 3, N), np.linspace(-3, 3, N))
psi = np.exp(-(x**2 + y**2)) * (1 + 0.05j)
kappa = np.exp(-(x**2 + y**2) / 2)

# Lorentz factor γ(t) - time dilation adjustment
def gamma_factor(t):
    return 1.0 / np.sqrt(1 + 0.0004 * t**2)

def laplacian_2d(field):
    return (
        np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
        - 4 * field
    ) / dx**2

energy_trace, coupling_trace, entropy_trace = [], [], []

for step in range(steps):
    γ = gamma_factor(step)
    
    lap_psi = laplacian_2d(psi)
    lap_kappa = laplacian_2d(kappa)

    psi_t = (1j * dt) * (lap_psi - kappa * psi) * γ
    kappa_t = dt * (0.01 * lap_kappa + 0.1 * np.abs(psi)**2 - 0.05 * kappa)

    psi = psi + psi_t
    kappa = kappa + kappa_t

    # --- Compute metrics ---
    energy = np.mean(np.abs(psi)**2 + np.abs(kappa)**2)
    coupling = np.mean(np.real(psi) * kappa)
    spectral_density = np.abs(np.fft.fftshift(np.fft.fft2(psi)))**2
    p_norm = spectral_density / np.sum(spectral_density)
    entropy = -np.sum(p_norm * np.log(p_norm + 1e-12))

    energy_trace.append(energy)
    coupling_trace.append(coupling)
    entropy_trace.append(entropy)

    if step % 100 == 0:
        print(f"Step {step:03d} - ⟨E⟩={energy:.4e}, ⟨ψ*κ⟩={coupling:.4e}, S={entropy:.4e}")

# --- Save Plots ---
plt.figure()
plt.plot(energy_trace, label="Energy ⟨E⟩")
plt.plot(coupling_trace, label="Coupling ⟨ψ*κ⟩")
plt.legend()
plt.title("H6 - Relativistic Curvature-Field Entanglement Stability")
plt.xlabel("Step")
plt.ylabel("Value")
energy_path = os.path.join(output_dir, "PAEV_TestH6_EnergyCoupling.png")
plt.savefig(energy_path, dpi=150)

plt.figure()
plt.plot(entropy_trace, color="purple", label="Spectral Entropy")
plt.legend()
plt.title("H6 - Spectral Entropy Evolution")
plt.xlabel("Step")
plt.ylabel("Entropy")
entropy_path = os.path.join(output_dir, "PAEV_TestH6_SpectralEntropy.png")
plt.savefig(entropy_path, dpi=150)

plt.figure()
plt.imshow(np.real(psi), cmap="plasma")
plt.colorbar(label="Re(ψ)")
plt.title("H6 - Final ψ Field (Real Part)")
field_path = os.path.join(output_dir, "PAEV_TestH6_FieldEntanglement.png")
plt.savefig(field_path, dpi=150)

# --- Print Summary ---
print("\n=== Test H6 - Relativistic Curvature-Field Entanglement Complete ===")
print(f"⟨E⟩ final = {energy_trace[-1]:.6e}")
print(f"⟨ψ*κ⟩ final = {coupling_trace[-1]:.6e}")
print(f"Spectral Entropy final = {entropy_trace[-1]:.6e}")
print("All output files saved:")
print(f" - {energy_path}")
print(f" - {entropy_path}")
print(f" - {field_path}")
print("----------------------------------------------------------")