# backend/photon_algebra/tests/paev_test_D9_quantum_gravity.py
import numpy as np
import matplotlib.pyplot as plt
import imageio

print("=== Test D9 — Quantum–Gravitational Coupling ===")

# Simulation grid
N = 121
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# Fields
psi = np.exp(-5 * (X**2 + Y**2)) * np.exp(1j * np.pi * X * Y)  # base wavefunction
curvature = np.exp(-3 * (X**2 + Y**2))                         # base curvature field

# Coupling constants
alpha = 0.4   # curvature-to-probability coupling
beta = 0.2    # back-reaction coupling

timesteps = 400
dt = 0.01

energy_trace = []
curvature_energy = []
prob_density = []
frames = []

for t in range(timesteps):
    laplace_psi = (
        np.roll(psi, 1, 0) + np.roll(psi, -1, 0) +
        np.roll(psi, 1, 1) + np.roll(psi, -1, 1) - 4 * psi
    )
    
    # Coupled evolution equations
    dpsi_dt = 1j * (laplace_psi - alpha * curvature * psi)
    dcurv_dt = beta * (np.abs(psi)**2 - np.mean(np.abs(psi)**2))
    
    psi += dt * dpsi_dt
    curvature += dt * dcurv_dt
    
    # Normalize psi
    psi /= np.sqrt(np.sum(np.abs(psi)**2))
    
    # Compute observables
    energy = np.mean(np.abs(np.gradient(np.angle(psi)))[0]**2)
    total_curv = np.mean(curvature)
    
    energy_trace.append(energy)
    curvature_energy.append(total_curv)
    prob_density.append(np.mean(np.abs(psi)**2))
    
    if t % 40 == 0:
        fig, ax = plt.subplots(figsize=(6,6))
        im = ax.imshow(np.angle(psi), cmap="twilight", extent=[-1,1,-1,1])
        ax.set_title(f"Test D9 — Coupled Quantum–Curvature Field\nStep {t}")
        plt.colorbar(im, ax=ax, label="Phase θ (rad)")
        fig.tight_layout()
        fig.canvas.draw()
        frame = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        frames.append(frame.reshape(fig.canvas.get_width_height()[::-1] + (4,)))
        plt.close(fig)

# Save animation
imageio.mimsave("PAEV_TestD9_QuantumGravity.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestD9_QuantumGravity.gif")

# Energy evolution plot
plt.figure()
plt.plot(energy_trace, color="blue")
plt.title("Test D9 — Energy Evolution (Quantum–Curvature Coupling)")
plt.xlabel("Time step")
plt.ylabel("Mean curvature energy ⟨|∇θ|²⟩")
plt.tight_layout()
plt.savefig("PAEV_TestD9_QuantumGravity_Energy.png")
plt.close()
print("✅ Saved energy evolution plot.")

# Curvature evolution plot
plt.figure()
plt.plot(curvature_energy, color="green")
plt.title("Test D9 — Mean Curvature Evolution (Einstein Feedback)")
plt.xlabel("Time step")
plt.ylabel("Mean curvature ⟨κ⟩")
plt.tight_layout()
plt.savefig("PAEV_TestD9_QuantumGravity_Curvature.png")
plt.close()
print("✅ Saved curvature evolution plot.")

# Probability density evolution
plt.figure()
plt.plot(prob_density, color="purple")
plt.title("Test D9 — Probability Density Evolution (|ψ|²)")
plt.xlabel("Time step")
plt.ylabel("⟨|ψ|²⟩ mean density")
plt.tight_layout()
plt.savefig("PAEV_TestD9_QuantumGravity_Probability.png")
plt.close()
print("✅ Saved probability density plot.")

print("\n=== Test D9 complete ===")
print(f"⟨E⟩ = {np.mean(energy_trace):.4f}")
print(f"⟨κ⟩ = {np.mean(curvature_energy):.4f}")
print(f"⟨|ψ|²⟩ = {np.mean(prob_density):.4f}")