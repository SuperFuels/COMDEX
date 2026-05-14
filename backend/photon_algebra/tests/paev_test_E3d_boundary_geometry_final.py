import numpy as np, json, time, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
from scipy.ndimage import gaussian_filter1d
from backend.photon_algebra.utils.load_constants import load_constants

const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

BOUNDARY_TYPES = ["periodic", "absorbing", "sponge"]
GEOMETRIES = ["circular", "elliptical"]
noise_amp = 0.02
seed0 = int(time.time())

metrics = {"Phi_mean": [], "curvature_exp": []}

def geometry_factor(x, geom):
    if geom == "circular":
        return np.exp(-x**2 / 150)
    elif geom == "elliptical":
        return np.exp(-x**2 / 180) * (1 + 0.1*np.cos(2*np.pi*x/60))
    return np.exp(-x**2 / 150)

def apply_boundary(Phi, btype):
    if btype == "periodic":
        Phi[0] = Phi[-1]
    elif btype == "absorbing":
        Phi[0] *= 0.95; Phi[-1] *= 0.95
    elif btype == "sponge":
        fade = np.linspace(1, 0.8, 40)
        Phi[:40] *= fade; Phi[-40:] *= fade[::-1]
    return Phi

for btype in BOUNDARY_TYPES:
    for geom in GEOMETRIES:
        np.random.seed(seed0)
        x = np.linspace(-25, 25, 512)
        t = np.linspace(0, 500, 2000)
        phi0 = np.random.uniform(0, 2*np.pi)
        base = geometry_factor(x, geom)
        Phi_stack = []

        for ti in range(0, len(t), 200):
            noise = np.random.normal(0, noise_amp, len(x))
            Phi = base * np.cos(0.02*t[ti] + phi0) + 0.002*np.cumsum(noise)
            Phi = apply_boundary(Phi, btype)
            Phi_stack.append(Phi)

        Phi_avg = np.mean(Phi_stack, axis=0)
        Phi_avg -= np.mean(Phi_avg)
        grad = np.gradient(Phi_avg, x)
        curvature = np.gradient(grad, x)
        curvature = gaussian_filter1d(curvature, sigma=2)
        rel_curv = np.abs(curvature) / (np.sqrt(np.mean(Phi_avg**2)) + 1e-8)
        valid = np.logical_and(np.abs(x) > 1, rel_curv > 1e-8)
        exp_fit = np.polyfit(np.log(np.abs(x[valid])), np.log(rel_curv[valid]), 1)[0]
        metrics["Phi_mean"].append(np.mean(Phi_avg))
        metrics["curvature_exp"].append(exp_fit)

def cv_rms(arr):
    arr = np.array(arr)
    return np.nanstd(arr) / (np.sqrt(np.mean(arr**2)) + 1e-12)

CVs = {k: float(cv_rms(v)) for k,v in metrics.items()}
classification = (
    "✅ Geometry invariant" if all(v < 0.06 for v in CVs.values())
    else "⚠️ Marginal robustness" if any(v < 0.08 for v in CVs.values())
    else "❌ Geometry dependent"
)

plt.figure(figsize=(8,5))
plt.scatter(metrics["Phi_mean"], metrics["curvature_exp"], s=80, c='darkblue')
plt.title("E3d - Boundary & Geometry Robustness (Final)")
plt.xlabel("⟨Φ⟩"); plt.ylabel("Curvature exponent (fit)")
plt.grid(True); plt.tight_layout()
plt.savefig("PAEV_E3d_BoundaryGeometry.png", dpi=160)

out = {
    "boundaries": BOUNDARY_TYPES,
    "geometries": GEOMETRIES,
    "noise_amp": noise_amp,
    "constants": {"ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β},
    "metrics": metrics,
    "CVs": CVs,
    "classification": classification,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
save_path = Path("backend/modules/knowledge/E3d_boundary_geometry_final.json")
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E3d - Boundary & Geometry Robustness (Final) ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved -> {save_path}")