"""
M1 - Wormhole Geometry Seed Test (Fixed Laplacian)
--------------------------------------------------
Simulates two curvature wells (κ1, κ2) with entangled ψ fields
to test for Einstein-Rosen (ER) bridge emergence (ER = EPR analogue).
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json

# === Load TOE constants ===
CONST_PATH = Path("backend/modules/knowledge/constants_v1.1.json")
if not CONST_PATH.exists():
    raise FileNotFoundError(f"Missing constants file: {CONST_PATH}")
constants = json.loads(CONST_PATH.read_text())
ħ = constants.get("ħ_eff", 1e-3)
G = constants.get("G_eff", 1e-5)
Λ = constants.get("Λ_eff", 1e-6)
α = constants.get("α_eff", 0.5)

# === Simulation grid ===
N = 256
x = np.linspace(-5, 5, N)
X, Y = np.meshgrid(x, x)

# Two curvature wells (black hole analogues)
def curvature_well(x0, y0, strength=1.0):
    return -strength / np.sqrt((X - x0)**2 + (Y - y0)**2 + 0.1)

κ1 = curvature_well(-1.5, 0, strength=1.0)
κ2 = curvature_well(1.5, 0, strength=1.0)
κ_total = κ1 + κ2

# Entangled ψ fields (complex conjugate phases)
np.random.seed(42)
phase = np.random.uniform(0, 2*np.pi, size=(N, N))
ψ1 = np.exp(1j * phase) * np.exp(-((X+1.5)**2 + Y**2))
ψ2 = np.exp(-1j * phase) * np.exp(-((X-1.5)**2 + Y**2))

# === Helper: 2D Laplacian ===
def laplacian(field: np.ndarray) -> np.ndarray:
    d2x = np.gradient(np.gradient(field, axis=0), axis=0)
    d2y = np.gradient(np.gradient(field, axis=1), axis=1)
    return d2x + d2y

# === Time evolution ===
steps = 400
dt = 0.01
mutual_info = []

for t in range(steps):
    lap1 = laplacian(ψ1)
    lap2 = laplacian(ψ2)

    ψ1_t = 1j * ħ * lap1 - α * κ_total * ψ1
    ψ2_t = 1j * ħ * lap2 - α * κ_total * ψ2

    ψ1 += dt * ψ1_t
    ψ2 += dt * ψ2_t

    # Mutual information proxy (cross-correlation of densities)
    corr = np.mean(np.real(ψ1 * np.conj(ψ2)))
    mutual_info.append(corr)

# === Diagnostics ===
ΔI = mutual_info[-1] - mutual_info[0]
print("=== M1 - Wormhole Geometry Seed Test ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
print(f"Initial Mutual Info = {mutual_info[0]:.3e}")
print(f"Final   Mutual Info = {mutual_info[-1]:.3e}")
print(f"ΔI (Correlation Drift) = {ΔI:.3e}")

if ΔI > 1e-3:
    print("✅ Nonlocal correlation sustained - ER bridge analogue detected.")
else:
    print("⚠️ No significant entanglement persistence - refine coupling terms.")

# === Plots ===
out_dir = Path(".")
plt.figure()
plt.plot(mutual_info, label="I(ψ1; ψ2)")
plt.xlabel("Time step")
plt.ylabel("Mutual Information (proxy)")
plt.title("Wormhole Formation - Mutual Information Flow")
plt.legend()
plt.grid(True)
plt.savefig(out_dir / "PAEV_M1_MutualInformation.png", dpi=200)

plt.figure()
plt.imshow(np.real(κ_total), extent=[-5,5,-5,5], cmap="magma")
plt.colorbar(label="Curvature κ")
plt.title("Dual Curvature Wells (Potential Throat Region)")
plt.savefig(out_dir / "PAEV_M1_CurvatureMap.png", dpi=200)

plt.figure()
plt.imshow(np.abs(ψ1 - ψ2), extent=[-5,5,-5,5], cmap="viridis")
plt.colorbar(label="|ψ1 - ψ2|")
plt.title("ψ Field Bridge Formation (Throat Map)")
plt.savefig(out_dir / "PAEV_M1_ThroatFormation.png", dpi=200)

print("✅ Plots saved:")
print("   - PAEV_M1_MutualInformation.png")
print("   - PAEV_M1_CurvatureMap.png")
print("   - PAEV_M1_ThroatFormation.png")
print("----------------------------------------------------------")
# === Save results summary ===
result = {
    "ħ": ħ,
    "G": G,
    "Λ": Λ,
    "α": α,
    "steps": steps,
    "initial_mutual_info": float(mutual_info[0]),
    "final_mutual_info": float(mutual_info[-1]),
    "delta_I": float(ΔI),
    "classification": "Stable Bridge" if ΔI > 1e-3 else "Unstable",
    "files": {
        "mutual_info_plot": "PAEV_M1_MutualInformation.png",
        "curvature_map": "PAEV_M1_CurvatureMap.png",
        "throat_map": "PAEV_M1_ThroatFormation.png"
    },
    "timestamp": "2025-10-07T15:50Z"
}

out_path = Path("backend/modules/knowledge/M1_wormhole_geometry.json")
out_path.write_text(json.dumps(result, indent=2))
print(f"📄 Summary saved -> {out_path}")