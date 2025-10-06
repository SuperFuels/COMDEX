"""
PAEV Test F6 — Black Hole Horizon Dynamics
Goal: simulate curvature singularity & test algebraic horizon formation,
entropy-area scaling, and Hawking-like radiation analogues.
"""

import numpy as np
import matplotlib.pyplot as plt

# === Parameters ===
N = 128
steps = 400
dt = 0.01
alpha = 0.08        # curvature diffusion
gamma = 0.04        # decay rate
chi = 0.20          # coupling strength
kappa_amp = 10.0    # initial curvature spike
sigma = 0.1         # horizon width

x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)
r2 = X**2 + Y**2

# === Initialize fields ===
psi = np.exp(-r2 / 0.4) * np.exp(1j * np.random.randn(N, N) * 0.2)
kappa = kappa_amp * np.exp(-r2 / sigma)
psi_t = np.zeros_like(psi, dtype=complex)

entropy_trace, area_trace, energy_trace = [], [], []

def laplacian(Z):
    return -4*Z + np.roll(Z,1,0) + np.roll(Z,-1,0) + np.roll(Z,1,1) + np.roll(Z,-1,1)

for step in range(steps):
    # === Field evolution ===
    lap_psi = laplacian(psi)
    psi_tt = lap_psi - chi * kappa * psi
    psi_t += dt * psi_tt
    psi += dt * psi_t

    # Curvature evolution
    lap_k = laplacian(kappa)
    kappa_t = alpha * lap_k - gamma * kappa + 0.01 * np.abs(psi)**2
    kappa += dt * kappa_t

    # === Entropy, area, and energy ===
    p = np.abs(psi)**2
    p /= np.sum(p)
    entropy = -np.sum(p * np.log(p + 1e-12))
    horizon_mask = (kappa > np.percentile(kappa, 95))
    area = np.sum(horizon_mask)
    energy = np.mean(np.abs(psi_t)**2 + np.abs(np.gradient(psi)[0])**2)

    entropy_trace.append(entropy)
    area_trace.append(area)
    energy_trace.append(energy)

# === Plot results ===
plt.figure(figsize=(6,4))
plt.plot(entropy_trace, label='Entropy (S)')
plt.plot(np.array(area_trace)/4, '--', label='Area/4')
plt.title('F6 — Horizon Entropy–Area Scaling')
plt.legend()
plt.savefig("PAEV_TestF6_EntropyArea.png")

plt.figure(figsize=(5,5))
plt.imshow(np.log10(np.abs(psi)**2 + 1e-6), cmap='inferno')
plt.title("F6 — ψ field intensity (log10)")
plt.colorbar(label='log10 |ψ|²')
plt.savefig("PAEV_TestF6_Field.png")

plt.figure(figsize=(5,5))
plt.imshow(kappa, cmap='plasma')
plt.title("F6 — Curvature κ (horizon)")
plt.colorbar(label='κ')
plt.savefig("PAEV_TestF6_Curvature.png")

print("=== Test F6 — Black Hole Horizon Dynamics Complete ===")
print(f"⟨Entropy⟩ final = {entropy_trace[-1]:.6e}")
print(f"⟨Area⟩ final    = {area_trace[-1]:.6e}")
print(f"⟨Energy⟩ final  = {energy_trace[-1]:.6e}")
print("Check if S ≈ A/4 (entropy–area relation).")
print("All output files saved in working directory.")