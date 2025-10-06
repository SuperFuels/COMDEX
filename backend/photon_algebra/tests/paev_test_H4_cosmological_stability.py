import numpy as np
import matplotlib.pyplot as plt

# === Parameters ===
N = 128
steps = 800
dt = 0.01

# Cosmological parameters (dimensionless scaling)
Lambda = 1e-4     # Cosmological constant analogue
H0 = 0.02         # Hubble-like parameter
kappa0 = 0.05     # Initial curvature amplitude
a = 1.0           # Scale factor (expands over time)
expansion_rate = 1e-3

# Initialize fields
x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)
phi = 1.0 + 0.02 * np.random.randn(N, N)
psi = np.exp(-((X**2 + Y**2) / 0.3)) * np.exp(1j * 0.5 * X)
kappa = kappa0 * np.exp(-(X**2 + Y**2) / 0.4)

energy_trace, entropy_trace, a_trace = [], [], []

# Laplacian helper
def laplacian(Z):
    return -4*Z + np.roll(Z,1,0) + np.roll(Z,-1,0) + np.roll(Z,1,1) + np.roll(Z,-1,1)

for step in range(steps):
    # Cosmological expansion
    a *= (1 + expansion_rate * dt)
    H = H0 * np.sqrt(Lambda + (np.mean(np.abs(kappa)) / kappa0))

    # Field evolution (scaled by expansion)
    lap_psi = laplacian(psi)
    lap_kappa = laplacian(kappa)
    psi_t = 1j * (lap_psi / a**2 - kappa * psi)
    kappa_t = (0.05 * lap_kappa - 0.02 * kappa + 0.001 * np.abs(psi)**2) * (1 / a)

    psi += dt * psi_t
    kappa += dt * kappa_t

    # Energy and entropy tracking
    energy = np.mean(np.abs(psi)**2 + np.abs(kappa)**2)
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(psi)))**2
    p = spectrum / np.sum(spectrum)
    spectral_entropy = -np.sum(p * np.log(p + 1e-12))

    energy_trace.append(energy)
    entropy_trace.append(spectral_entropy)
    a_trace.append(a)

# === Plot Results ===
plt.figure(figsize=(6,4))
plt.plot(energy_trace, label='Energy ⟨E⟩')
plt.plot(entropy_trace, label='Spectral Entropy')
plt.title('H4 — Cosmological Energy & Entropy Evolution')
plt.xlabel('Step')
plt.legend()
plt.savefig('PAEV_TestH4_EnergyEntropy.png')

plt.figure(figsize=(6,4))
plt.plot(a_trace)
plt.title('H4 — Scale Factor a(t)')
plt.xlabel('Step')
plt.ylabel('a(t)')
plt.savefig('PAEV_TestH4_ScaleFactor.png')

# Field snapshot
plt.figure(figsize=(6,3))
plt.imshow(np.real(psi), cmap='magma')
plt.title('H4 — ψ Field (Final Real Part)')
plt.colorbar()
plt.savefig('PAEV_TestH4_FinalField.png')

print("\n=== Test H4 — Cosmological Scale Stability Complete ===")
print(f"⟨E⟩ final = {energy_trace[-1]:.6e}")
print(f"⟨S⟩ final = {entropy_trace[-1]:.6e}")
print(f"a(final)   = {a_trace[-1]:.6e}")
print("All output files saved:")
print(" - PAEV_TestH4_EnergyEntropy.png")
print(" - PAEV_TestH4_ScaleFactor.png")
print(" - PAEV_TestH4_FinalField.png")
print("----------------------------------------------------------")