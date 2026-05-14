# ==========================================================
# Test E3 - Information Density Mapping (Quantum Information Curvature)
# ==========================================================
# Purpose:
#   Couple curvature κ(x,y) and quantum information density I(x,y)
#   derived from the local field amplitude |ψ|2 log |ψ|2.
#   Observe mutual feedback and emergent geometric information pattern.
#
# Outputs:
#   - Animation of curvature and information density
#   - Information-curvature correlation plot
#   - Entropy vs information trace
#   - Spectrum of information field
#
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# --- Simulation setup ---
N = 200
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# Complex information field
psi = (np.random.randn(N, N) + 1j * np.random.randn(N, N)) * 0.01
kappa = 0.01 * np.random.randn(N, N)

dt = 0.01
steps = 400
alpha = 0.05  # damping
beta = 0.1    # coupling strength

frames = []
corr_trace = []
entropy_trace = []
info_trace = []

def laplacian(Z):
    return (
        -4 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

# --- Evolution loop ---
for step in range(steps):
    # Update ψ with curvature feedback
    lap = laplacian(psi)
    psi += dt * (1j * beta * kappa * psi + 0.02 * lap - alpha * psi)

    # Update curvature
    d2k = laplacian(kappa)
    kappa += dt * (beta * np.real(psi * np.conj(lap)) - alpha * kappa)

    # Compute fields
    prob = np.abs(psi)**2
    info = prob * np.log(prob + 1e-12)
    entropy = -np.mean(info)

    corr = np.mean((kappa - np.mean(kappa)) * (info - np.mean(info)))

    corr_trace.append(corr)
    entropy_trace.append(entropy)
    info_trace.append(np.mean(info))

    if step % 20 == 0:
        fig, axs = plt.subplots(1, 2, figsize=(10,5))
        im0 = axs[0].imshow(kappa, cmap="twilight", extent=[-1,1,-1,1])
        axs[0].set_title(f"Curvature κ(x,y) - Step {step}")
        plt.colorbar(im0, ax=axs[0])

        im1 = axs[1].imshow(info, cmap="inferno", extent=[-1,1,-1,1])
        axs[1].set_title("Information Density I(x,y)")
        plt.colorbar(im1, ax=axs[1])
        plt.tight_layout()

        fig.canvas.draw()
        img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# --- Save results ---
imageio.mimsave("PAEV_TestE3_InfoCurvature.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestE3_InfoCurvature.gif")

# Correlation plot
plt.figure()
plt.plot(corr_trace, color='purple')
plt.title("Test E3 - Information-Curvature Correlation Evolution")
plt.xlabel("Time step")
plt.ylabel("⟨κ*I⟩ correlation")
plt.tight_layout()
plt.savefig("PAEV_TestE3_InfoCurvature_Correlation.png")
plt.close()
print("✅ Saved correlation plot: PAEV_TestE3_InfoCurvature_Correlation.png")

# Entropy vs Information trace
plt.figure()
plt.plot(entropy_trace, color='orange', label='Entropy ⟨S⟩')
plt.plot(info_trace, color='blue', label='Information ⟨I⟩')
plt.title("Test E3 - Entropy vs Information Trace")
plt.xlabel("Time step")
plt.ylabel("Mean field values")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestE3_InfoCurvature_EntropyInfo.png")
plt.close()
print("✅ Saved entropy-information plot: PAEV_TestE3_InfoCurvature_EntropyInfo.png")

# Spectrum of information field
fft_info = np.fft.fftshift(np.abs(np.fft.fft2(info))**2)
plt.figure(figsize=(6,6))
plt.imshow(np.log(fft_info + 1e-8), cmap='magma', extent=[-1,1,-1,1])
plt.title("Test E3 - Information Field Spectrum (log power)")
plt.colorbar(label="log |I(k)|2")
plt.tight_layout()
plt.savefig("PAEV_TestE3_InfoCurvature_Spectrum.png")
plt.close()
print("✅ Saved information field spectrum: PAEV_TestE3_InfoCurvature_Spectrum.png")

print("\n=== Test E3 - Information Density Mapping Complete ===")
print(f"⟨κ*I⟩ final = {np.mean(corr_trace):.4e}")
print(f"⟨Entropy⟩ final = {np.mean(entropy_trace):.4e}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")