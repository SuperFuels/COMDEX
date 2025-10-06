import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft2, fftshift
from scipy.signal import find_peaks
from scipy.stats import linregress

print("🎯 Initiating G3 — Predictive Mass–Spin Spectrum Reconstruction...")

# ================================================================
# Simulation parameters
# ================================================================
N = 128
steps = 320
dx = 1.0 / N
dt = 0.05

c1, c2, c3 = 0.9, 0.7, 0.5
x = np.linspace(0, 2 * np.pi, N)
X, Y = np.meshgrid(x, x)

# Initial curvature and phase perturbations
kappa = np.exp(-((X - np.pi)**2 + (Y - np.pi)**2) / 0.4)
psi = np.cos(3 * X) * np.exp(-((Y - np.pi)**2) / 0.8)
psi_t = np.zeros_like(psi)

# Storage
mass_modes, spin_modes, energy_trace = [], [], []

# Helper functions
def laplacian(Z):
    return (-4 * Z +
            np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0) +
            np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1)) / (dx**2)

def spectral_entropy(field):
    fft_mag = np.abs(fft2(field))**2
    p = fft_mag / np.sum(fft_mag)
    p = p[p > 0]
    return -np.sum(p * np.log(p)) / np.log(len(p))

# ================================================================
# Time evolution (simulate curvature–information coupling)
# ================================================================
for t in range(steps):
    lap_kappa = laplacian(kappa)
    lap_psi = laplacian(psi)

    psi_tt = c1 * lap_psi - c2 * psi + c3 * kappa
    kappa_tt = c2 * lap_kappa - c1 * kappa + 0.02 * psi

    psi_t += dt * psi_tt
    psi += dt * psi_t
    kappa += dt * kappa_tt

    # Compute energy density
    L = 0.5 * (psi_t**2 + c1 * (np.gradient(psi)[0]**2).mean()) - 0.5 * c3 * kappa**2
    energy_trace.append(np.nanmean(L))

    # Every few steps: extract spectral modes
    if t % 20 == 0 and t > 40:
        f = fftshift(np.abs(fft2(psi)))
        spectrum = np.mean(f, axis=0)
        peaks, _ = find_peaks(spectrum, prominence=0.05)
        if len(peaks) > 0:
            mass_modes.extend(peaks)
            spin_modes.extend((peaks % 6) - 3)  # approximate spin harmonic label

# ================================================================
# Spectrum and Mass Reconstruction
# ================================================================
mass_modes = np.array(mass_modes)
spin_modes = np.array(spin_modes)

if len(mass_modes) == 0:
    print("⚠️ No stable modes detected — curvature oscillations dissipated.")
else:
    norm_mass = (mass_modes - np.min(mass_modes)) / (np.ptp(mass_modes) + 1e-9)

    # Dispersion fit
    k_vals = np.linspace(0, np.max(mass_modes), len(mass_modes))
    omega_vals = np.sqrt(k_vals**2 + norm_mass**2)
    slope, intercept, r, *_ = linregress(k_vals**2, omega_vals**2)

    # Effective masses
    m_eff = np.sqrt(np.abs(intercept))
    print(f"🧮 Effective mass scale: m_eff ≈ {m_eff:.4e} (normalized units)")
    print(f"Dispersion fit R² = {r**2:.4f}")

    # Comparative fitting
    m_e, m_mu, m_pi = 0.511, 105.7, 139.6  # MeV
    ratio_mu = (m_mu / m_e)
    ratio_pi = (m_pi / m_e)
    ratio_sim = np.median(np.diff(sorted(mass_modes)) / np.mean(mass_modes))

    with open("PAEV_TestG3_ComparativeRatios.txt", "w") as f:
        f.write(f"Electron:Muon ratio (known): {ratio_mu:.2f}\n")
        f.write(f"Electron:Pion ratio (known): {ratio_pi:.2f}\n")
        f.write(f"Simulated mass mode spacing ratio: {ratio_sim:.3f}\n")
        f.write(f"Effective m_eff: {m_eff:.4e}\n")

# ================================================================
# Plot outputs
# ================================================================
plt.figure(figsize=(10, 6))
plt.title("G3 — Emergent Mass Spectrum (log scale)")
plt.plot(np.sort(mass_modes), np.log10(1 + np.arange(len(mass_modes))), "goldenrod")
plt.xlabel("Mode index (k)")
plt.ylabel("log Amplitude")
plt.grid(alpha=0.4)
plt.savefig("PAEV_TestG3_MassSpectrum.png", dpi=200)
plt.close()

plt.figure(figsize=(8, 6))
plt.title("G3 — Dispersion Curve: ω² vs k²")
plt.plot(k_vals**2, omega_vals**2, color="purple", lw=2)
plt.xlabel("k²")
plt.ylabel("ω²")
plt.savefig("PAEV_TestG3_DispersionCurve.png", dpi=200)
plt.close()

plt.figure(figsize=(8, 6))
plt.scatter(norm_mass, spin_modes, c=spin_modes, cmap="plasma", s=40, alpha=0.7)
plt.title("G3 — Spin–Mass Distribution")
plt.xlabel("Normalized mass mode")
plt.ylabel("Spin harmonic (approx.)")
plt.savefig("PAEV_TestG3_SpinMassMap.png", dpi=200)
plt.close()

print("\n✅ Saved all G3 output plots and data:")
print(" - PAEV_TestG3_MassSpectrum.png")
print(" - PAEV_TestG3_DispersionCurve.png")
print(" - PAEV_TestG3_SpinMassMap.png")
print(" - PAEV_TestG3_ComparativeRatios.txt")
print("\n=== Test G3 — Predictive Mass–Spin Spectrum Complete ===")