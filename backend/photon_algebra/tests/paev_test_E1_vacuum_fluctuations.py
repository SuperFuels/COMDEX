# ==========================================================
# Test E1 - Curvature Vacuum Fluctuations (Emergent Quantum Foam)
# ==========================================================
# Purpose:
#   Observe spontaneous curvature and phase-field fluctuations
#   in the vacuum limit (no imposed sources).
#   Detect stochastic but self-correlated quantum foam patterns.
#
# Outputs:
#   - Animation of curvature fluctuations
#   - Spectrum of curvature variance (Fourier)
#   - Correlation function of curvature noise
#   - Energy trace (residual vacuum dynamics)
#
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import os

# Simulation setup
N = 200
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# Small random initial curvature field - "vacuum jitter"
kappa = 0.001 * np.random.randn(N, N)

# Parameters
dt = 0.01
steps = 400
alpha = 0.2      # damping (vacuum relaxation)
beta = 0.05      # feedback strength (spontaneous curvature growth)

frames = []
energy_trace = []
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
    kappa += dt * (beta * d2k - alpha * kappa + 0.001 * np.random.randn(N, N))

    energy = np.mean(kappa**2)
    energy_trace.append(energy)

    # Compute autocorrelation in central slice
    c = np.correlate(kappa[N//2, :], kappa[N//2, :], mode='full')
    c /= np.max(np.abs(c))
    corr_trace.append(c[N-1])

    # Capture frames periodically
    if step % 20 == 0:
        fig, ax = plt.subplots(figsize=(5,5))
        im = ax.imshow(kappa, cmap='plasma', extent=[-1,1,-1,1])
        ax.set_title(f"Test E1 - Curvature Vacuum Fluctuations\nStep {step}")
        plt.colorbar(im, ax=ax, label="κ curvature")
        plt.tight_layout()

        fig.canvas.draw()
        buf = np.asarray(fig.canvas.renderer.buffer_rgba())
        frames.append(buf.copy())
        plt.close(fig)

# ----------------------------------------------------------
# Save outputs
# ----------------------------------------------------------

def save_and_print(fig, filename, message):
    plt.tight_layout()
    fig.savefig(filename)
    plt.close(fig)
    print(f"✅ Saved {message}: {os.path.abspath(filename)}")

# Animation
anim_path = "PAEV_TestE1_VacuumFluctuations.gif"
imageio.mimsave(anim_path, frames, fps=10)
print(f"✅ Saved animation to: {os.path.abspath(anim_path)}")

# Energy trace
fig = plt.figure()
plt.plot(energy_trace, color='blue')
plt.title("Test E1 - Residual Vacuum Energy Evolution")
plt.xlabel("Time step")
plt.ylabel("⟨κ2⟩ vacuum energy")
save_and_print(fig, "PAEV_TestE1_VacuumFluctuations_Energy.png", "energy trace")

# Correlation trace
fig = plt.figure()
plt.plot(corr_trace, color='purple')
plt.title("Test E1 - Vacuum Curvature Correlation Decay")
plt.xlabel("Time step")
plt.ylabel("Autocorrelation amplitude")
save_and_print(fig, "PAEV_TestE1_VacuumFluctuations_Correlation.png", "correlation decay plot")

# Fourier spectrum
fft_spectrum = np.fft.fftshift(np.abs(np.fft.fft2(kappa))**2)
fig = plt.figure(figsize=(6,6))
plt.imshow(np.log(fft_spectrum + 1e-8), cmap='magma', extent=[-1,1,-1,1])
plt.title("Test E1 - Vacuum Curvature Spectrum (log power)")
plt.colorbar(label="log |κ(k)|2")
save_and_print(fig, "PAEV_TestE1_VacuumFluctuations_Spectrum.png", "Fourier spectrum")

# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------
print("\n=== Test E1 - Curvature Vacuum Fluctuations Complete ===")
print(f"⟨κ2⟩ final = {np.mean(kappa**2):.4e}")
print(f"⟨corr⟩ final = {np.mean(corr_trace):.4f}")
print("📁 All output files saved in:")
print(f"   {os.getcwd()}")
print("----------------------------------------------------------")