import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ============================================================
# Test D10 — Full Field Unification Benchmark (Unified Stability Test)
# ============================================================

N = 121
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
dt = 0.05
steps = 400

# Unified field components
psi = np.exp(1j * (np.pi * X * Y)) * np.exp(-((X**2 + Y**2) * 2))
kappa = 0.3 * np.exp(-2*(X**2 + Y**2))
Q = np.zeros_like(X)
Q[N//2-2:N//2+2, N//2-2:N//2+2] = 1.0

alpha, beta, gamma, lam = 1.0, 0.5, 0.25, 0.1

def laplacian(Z):
    return np.roll(Z,1,axis=0)+np.roll(Z,-1,axis=0)+np.roll(Z,1,axis=1)+np.roll(Z,-1,axis=1)-4*Z

energy_trace, charge_trace, curvature_trace, psi_norm = [], [], [], []
frames = []

for t in range(steps):
    # Coupled evolution
    dpsi = 1j * alpha * laplacian(psi) - lam * kappa * psi
    dkappa = beta * laplacian(kappa) + lam * np.real(np.gradient(np.angle(psi))[0])
    dQ = gamma * laplacian(Q) - lam * np.imag(psi)
    
    psi += dt * dpsi
    kappa += dt * dkappa
    Q += dt * dQ

    # Diagnostics
    energy = alpha*np.mean(np.abs(np.gradient(np.angle(psi)))**2) + beta*np.mean(kappa**2) + gamma*np.mean(Q**2)
    charge = np.mean(Q)
    curvature_mean = np.mean(kappa)
    norm = np.mean(np.abs(psi)**2)
    
    energy_trace.append(energy)
    charge_trace.append(charge)
    curvature_trace.append(curvature_mean)
    psi_norm.append(norm)

    if t % 40 == 0:
        fig, ax = plt.subplots(figsize=(6,6))
        ax.imshow(np.angle(psi), cmap="twilight", extent=[-1,1,-1,1])
        ax.set_title(f"Test D10 — Unified Field Phase\nStep {t}")
        plt.tight_layout()
        fig.canvas.draw()
        img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
        frames.append(img)
        plt.close()

# Save artifacts
imageio.mimsave("PAEV_TestD10_UnifiedField.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestD10_UnifiedField.gif")

plt.figure()
plt.plot(energy_trace, color="blue")
plt.title("Test D10 — Total Energy Evolution (Unified Stability)")
plt.xlabel("Time step")
plt.ylabel("⟨H⟩ total energy")
plt.tight_layout()
plt.savefig("PAEV_TestD10_UnifiedField_Energy.png")
plt.close()
print("✅ Saved energy evolution plot.")

plt.figure()
plt.plot(curvature_trace, color="green")
plt.title("Test D10 — Mean Curvature Evolution")
plt.xlabel("Time step")
plt.ylabel("⟨κ⟩ mean curvature")
plt.tight_layout()
plt.savefig("PAEV_TestD10_UnifiedField_Curvature.png")
plt.close()
print("✅ Saved curvature evolution plot.")

plt.figure()
plt.plot(charge_trace, color="red")
plt.title("Test D10 — Topological Charge Conservation")
plt.xlabel("Time step")
plt.ylabel("⟨Q⟩ total charge")
plt.tight_layout()
plt.savefig("PAEV_TestD10_UnifiedField_Charge.png")
plt.close()
print("✅ Saved charge conservation plot.")

print("\n=== Test D10 — Full Field Unification Complete ===")
print(f"⟨Energy⟩ = {np.mean(energy_trace):.4f}")
print(f"⟨κ⟩ = {np.mean(curvature_trace):.4f}")
print(f"⟨|ψ|²⟩ = {np.mean(psi_norm):.4e}")
print(f"⟨Q⟩ = {np.mean(charge_trace):.4f}")