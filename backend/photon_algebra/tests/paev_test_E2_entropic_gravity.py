# ==========================================================
# Test E2 - Entropic Gravity Simulation
# ==========================================================
# Purpose:
#   Couple curvature κ(x,y) to local entropy S(x,y)
#   to simulate emergent entropic gravity.
#   Entropy gradients act as curvature sources.
#
# Outputs:
#   - Animation of coupled curvature-entropy fields
#   - Energy vs entropy trace
#   - Entropy-curvature correlation plot
#
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# Simulation parameters
N = 200
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

dt = 0.01
steps = 400
alpha = 0.05    # damping
beta = 0.15     # entropy coupling strength
gamma = 0.02    # feedback (stability regulator)

# Initialize curvature and entropy fields
kappa = 0.01 * np.exp(-5 * (X**2 + Y**2))          # small initial curvature bump
S = 0.1 * np.random.rand(N, N)                     # random local entropy density

frames = []
energy_trace = []
entropy_trace = []
corr_trace = []

def laplacian(Z):
    return (
        -4 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

# Main evolution loop
for step in range(steps):
    d2k = laplacian(kappa)
    d2S = laplacian(S)

    # Coupled entropic-curvature evolution equations
    kappa += dt * (beta * d2S - alpha * kappa + gamma * d2k)
    S += dt * (0.1 * d2S + 0.2 * kappa)

    # Diagnostics
    energy = np.mean(kappa**2)
    entropy = np.mean(S)
    corr = np.mean(kappa * S)

    energy_trace.append(energy)
    entropy_trace.append(entropy)
    corr_trace.append(corr)

    if step % 20 == 0:
        fig, ax = plt.subplots(1, 2, figsize=(9, 4))
        im1 = ax[0].imshow(kappa, cmap="plasma", extent=[-1,1,-1,1])
        ax[0].set_title(f"Curvature κ(x,y) - Step {step}")
        plt.colorbar(im1, ax=ax[0], fraction=0.046, pad=0.04)

        im2 = ax[1].imshow(S, cmap="cividis", extent=[-1,1,-1,1])
        ax[1].set_title("Entropy Field S(x,y)")
        plt.colorbar(im2, ax=ax[1], fraction=0.046, pad=0.04)

        plt.suptitle("Test E2 - Entropic Gravity Simulation")
        plt.tight_layout()

        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# Save animation
imageio.mimsave("PAEV_TestE2_EntropicGravity.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestE2_EntropicGravity.gif")

# Plot energy and entropy evolution
plt.figure()
plt.plot(energy_trace, label="⟨κ2⟩ (curvature energy)", color="blue")
plt.plot(entropy_trace, label="⟨S⟩ (entropy mean)", color="orange")
plt.title("Test E2 - Energy vs Entropy Evolution")
plt.xlabel("Time step")
plt.ylabel("Mean value")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestE2_EntropicGravity_EnergyEntropy.png")
plt.close()
print("✅ Saved energy-entropy evolution plot.")

# Correlation trace
plt.figure()
plt.plot(corr_trace, color="purple")
plt.title("Test E2 - Curvature-Entropy Correlation")
plt.xlabel("Time step")
plt.ylabel("⟨κ*S⟩ correlation")
plt.tight_layout()
plt.savefig("PAEV_TestE2_EntropicGravity_Correlation.png")
plt.close()
print("✅ Saved curvature-entropy correlation plot.")

print("\n=== Test E2 - Entropic Gravity Simulation Complete ===")
print(f"⟨κ2⟩ final = {np.mean(kappa**2):.4e}")
print(f"⟨S⟩ final = {np.mean(S):.4e}")
print(f"⟨κ*S⟩ correlation = {np.mean(corr_trace):.4e}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")