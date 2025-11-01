import numpy as np
import matplotlib.pyplot as plt

# --- Parameters ---
N = 128
steps = 600
dt = 0.01
T_init = 0.25  # initial "temperature"
alpha = 0.01   # cooling rate
gamma = 0.12   # coupling coefficient

x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)
psi = np.random.normal(0, T_init, (N, N)) + 1j * np.random.normal(0, T_init, (N, N))
kappa = np.zeros_like(psi, dtype=float)

energy_trace, entropy_trace, temp_trace = [], [], []

def laplacian(Z):
    return -4*Z + np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)

# --- Evolution ---
for step in range(steps):
    lap_psi = laplacian(psi)
    psi_t = (1j * dt) * (lap_psi - kappa * psi)
    psi += psi_t

    lap_k = laplacian(kappa)
    kappa += dt * (0.04 * lap_k + gamma * np.real(psi)**2 - 0.05 * kappa)

    # Gradual cooling
    T = T_init * np.exp(-alpha * step / steps)
    temp_trace.append(T)

    # Energy & entropy proxies
    energy = np.mean(np.abs(psi)**2)
    energy_trace.append(energy)

    spectral_density = np.abs(np.fft.fftshift(np.fft.fft2(psi)))**2
    p = spectral_density / np.sum(spectral_density)
    entropy = -np.sum(p * np.log(p + 1e-12))
    entropy_trace.append(entropy)

# --- Planck-like spectrum ---
freq = np.fft.fftfreq(N)
spectrum = np.mean(np.abs(np.fft.fft2(psi))**2, axis=0)
planck_like = freq**3 / (np.exp(freq / (T_init + 1e-5)) - 1)
planck_like /= np.max(planck_like)

# --- Plot results ---
plt.figure(figsize=(8,5))
plt.plot(freq[:N//2], spectrum[:N//2] / np.max(spectrum), label='Simulated Spectrum')
plt.plot(freq[:N//2], planck_like[:N//2], '--', label='Planck Fit')
plt.title("H2 - Thermal Spectrum Consistency")
plt.xlabel("Frequency")
plt.ylabel("Normalized Intensity")
plt.legend()
plt.savefig("PAEV_TestH2_ThermalSpectrum.png")

plt.figure()
plt.plot(energy_trace, label='Energy ⟨E⟩')
plt.plot(entropy_trace, label='Spectral Entropy')
plt.title("H2 - Energy & Entropy Evolution")
plt.xlabel("Step")
plt.legend()
plt.savefig("PAEV_TestH2_EnergyEntropy.png")

print("\n=== Test H2 - Thermal Coherence & Blackbody Consistency Complete ===")
print(f"⟨E⟩ final = {energy_trace[-1]:.6e}")
print(f"⟨S⟩ final = {entropy_trace[-1]:.6e}")
print(f"T_final   = {temp_trace[-1]:.6e}")
print("All output files saved:")
print(" - PAEV_TestH2_ThermalSpectrum.png")
print(" - PAEV_TestH2_EnergyEntropy.png")
print("----------------------------------------------------------")