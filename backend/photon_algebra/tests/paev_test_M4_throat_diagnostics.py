import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# === M4 - Wormhole Throat Diagnostics ===
print("=== M4 - Wormhole Throat Diagnostics ===")

ħ = 1e-3
G = 1e-5
Λ = 1e-6
α = 0.5

# Spatial domain
x = np.linspace(-5, 5, 500)
y = np.linspace(-5, 5, 500)
X, Y = np.meshgrid(x, y)

# Dual curvature wells (mirroring M1 setup)
κ1 = -1.0 / np.sqrt((X + 2)**2 + Y**2 + 0.1)
κ2 = -1.0 / np.sqrt((X - 2)**2 + Y**2 + 0.1)
κ_total = κ1 + κ2

# Field amplitudes (ψ1, ψ2)
ψ1 = np.exp(-((X + 2)**2 + Y**2)) * np.exp(1j * α * κ1)
ψ2 = np.exp(-((X - 2)**2 + Y**2)) * np.exp(1j * α * κ2)

# Bridge field and throat map
bridge = np.abs(ψ1 - ψ2)
midline = bridge[bridge.shape[0]//2, :]

# Compute approximate throat width (FWHM)
half_max = np.max(midline) / 2
indices = np.where(midline >= half_max)[0]
if len(indices) >= 2:
    throat_width = x[indices[-1]] - x[indices[0]]
else:
    throat_width = 0.0

# NEC proxy (simplified energy density-like term)
NEC_proxy = ħ * np.abs(np.gradient(np.angle(ψ1)))**2 - α * np.abs(κ_total)
NEC_line = NEC_proxy[NEC_proxy.shape[0]//2, :]

# Geodesic distance proxy
geo_proxy = np.exp(-np.abs(κ_total))
geo_line = geo_proxy[geo_proxy.shape[0]//2, :]

# === Save Plots ===
outdir = Path("backend/photon_algebra/tests/plots")
outdir.mkdir(parents=True, exist_ok=True)

plt.figure(figsize=(7,5))
plt.plot(x, midline, label="|ψ1 - ψ2|")
plt.axhline(half_max, color='r', linestyle='--', label='Half max')
plt.title("M4 - Throat Profile (|ψ1-ψ2|)")
plt.xlabel("x-axis (midline)")
plt.ylabel("Amplitude")
plt.legend()
plt.tight_layout()
plt.savefig(outdir / "PAEV_M4_ThroatProfile.png")

plt.figure(figsize=(7,5))
plt.plot(x, NEC_line, label="NEC proxy (ρ + Σpi)")
plt.axhline(0, color='r', linestyle='--', label='NEC = 0')
plt.title("M4 - NEC Violation Proxy")
plt.xlabel("x-axis (midline)")
plt.ylabel("NEC proxy")
plt.legend()
plt.tight_layout()
plt.savefig(outdir / "PAEV_M4_NEC_Proxy.png")

plt.figure(figsize=(6,5))
plt.imshow(geo_proxy, extent=[-5,5,-5,5], origin='lower', cmap='viridis')
plt.title("M4 - Geodesic Distance Proxy")
plt.colorbar(label="exp(-|κ|)")
plt.tight_layout()
plt.savefig(outdir / "PAEV_M4_GeodesicMap.png")

# === Results Summary ===
NEC_min = np.min(NEC_line)
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
print(f"Throat width (FWHM): {throat_width:.3f}")
print(f"NEC min value: {NEC_min:.3e}")
print("✅ Throat diagnostics complete.")
print("✅ Plots saved:")
print("   - PAEV_M4_ThroatProfile.png")
print("   - PAEV_M4_NEC_Proxy.png")
print("   - PAEV_M4_GeodesicMap.png")
print("----------------------------------------------------------")