import numpy as np, json, time, matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
from scipy.ndimage import gaussian_filter1d

# --- constants loader ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- parameter sets ---
BOUNDARY_TYPES = ["periodic", "absorbing", "sponge"]
GEOMETRIES = ["circular", "elliptical"]
noise_amp = 0.01
seed0 = int(time.time())

metrics = {"Phi_mean": [], "curvature_exp": []}

# --- synthetic geometry factor ---
def geometry_factor(x, geom):
    if geom == "circular":
        return np.exp(-x**2 / 150)
    elif geom == "elliptical":
        return np.exp(-x**2 / 200) * (1 + 0.2*np.cos(2*np.pi*x/40))
    return np.exp(-x**2 / 150)

# --- boundary handler ---
def apply_boundary(Phi, btype):
    if btype == "periodic":
        Phi[0] = Phi[-1]
    elif btype == "absorbing":
        Phi[0] *= 0.9; Phi[-1] *= 0.9
    elif btype == "sponge":
        fade = np.linspace(1, 0.7, 40)
        Phi[:40] *= fade
        Phi[-40:] *= fade[::-1]
    return Phi

# --- run simulations ---
for btype in BOUNDARY_TYPES:
    for geom in GEOMETRIES:
        np.random.seed(seed0)
        x = np.linspace(-25, 25, 512)
        t = np.linspace(0, 1000, 4000)
        phi0 = np.random.uniform(0, 2*np.pi)
        base = geometry_factor(x, geom)
        Phi = np.zeros_like(x)

        for ti in range(len(t)):
            noise = np.random.normal(0, noise_amp, len(x))
            Phi = base * np.cos(0.01 * t[ti] + phi0) + 0.001*np.cumsum(noise)
            Phi = apply_boundary(Phi, btype)

        # remove geometry bias
        Phi -= np.mean(Phi)

        # normalize curvature fit
        grad = np.gradient(Phi, x)
        curvature = np.gradient(grad, x)
        curvature = gaussian_filter1d(curvature, sigma=3)
        abs_curv = np.abs(curvature) / (np.abs(Phi) + 1e-6)

        # safe log-fit region
        valid = np.logical_and(np.abs(x) > 1, np.abs(abs_curv) > 1e-8)
        if np.sum(valid) > 20:
            exp_fit = np.polyfit(np.log(np.abs(x[valid])),
                                 np.log(abs_curv[valid]), 1)[0]
        else:
            exp_fit = np.nan

        metrics["Phi_mean"].append(np.mean(Phi))
        metrics["curvature_exp"].append(exp_fit)

# --- analysis ---
def cv(arr): 
    arr = np.array(arr)
    return np.nanstd(arr)/np.nanmean(np.abs(arr))

CVs = {k: float(cv(v)) for k,v in metrics.items()}
classification = (
    "✅ Geometry invariant" if all(v < 0.03 for v in CVs.values())
    else "⚠️ Marginal robustness" if any(v < 0.05 for v in CVs.values())
    else "❌ Geometry dependent"
)

# --- plot ---
plt.figure(figsize=(8,5))
plt.scatter(metrics["Phi_mean"], metrics["curvature_exp"], s=80, c='mediumblue')
plt.title("E3b — Boundary & Geometry Robustness (Refined)")
plt.xlabel("⟨Φ⟩"); plt.ylabel("Curvature exponent (fit)")
plt.grid(True); plt.tight_layout()
plt.savefig("PAEV_E3b_BoundaryGeometry.png", dpi=160)

# --- save ---
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
save_path = Path("backend/modules/knowledge/E3b_boundary_geometry_refined.json")
with open(save_path, "w") as f:
    json.dump(out, f, indent=2)

print("=== E3b — Boundary & Geometry Robustness (Refined) ===")
print(json.dumps(out, indent=2))
print(f"✅ Results saved → {save_path}")