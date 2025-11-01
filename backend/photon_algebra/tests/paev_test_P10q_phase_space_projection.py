import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from datetime import datetime, timezone
import json

# ================================================
# P10q - Global Resonance Phase-Space Projection
# ================================================

np.random.seed(42)

# --- Load previous P10p parameters (or reuse inline) ---
K_field = 0.1
K_global = 0.12
eta = 0.001
noise = 0.0025
T = 1600
M = 3

alignment = dict(
    kappa_align_base=0.06,
    kappa_boost=0.18,
    curvature_gain=0.2,
    phase_damp=0.022,
    merge_bias_gain=0.009,
    bias_gain=0.004
)

# --- Generate synthetic (or load) trajectories φ(t) ---
phi = np.zeros((M, T))
phi[0, 0], phi[1, 0], phi[2, 0] = 0.0, 0.40, -0.25
omega = np.array([0.002, -0.001, 0.0005])

def complex_order_parameter(phivec):
    z = np.exp(1j * phivec)
    zbar = z.mean()
    R = np.abs(zbar)
    psi = np.angle(zbar)
    return R, psi

for t in range(1, T):
    R, psi = complex_order_parameter(phi[:, t-1])
    damp = 0.04 * (1 + 0.6 * (1 - R))
    for i in range(M):
        global_term = K_global * np.sin(psi - phi[i, t-1])
        align_term = -alignment["kappa_align_base"] * np.sin(phi[i, t-1] - np.mean(phi[:, t-1]))
        curvature = -alignment["curvature_gain"] * np.sin(2 * (phi[i, t-1] - np.mean(phi[:, t-1])))
        noise_term = np.random.normal(0, noise)
        phi[i, t] = phi[i, t-1] + eta * (omega[i] + global_term + align_term + curvature - damp * phi[i, t-1] + noise_term)

# --- Compute features for embedding ---
R_hist = np.zeros(T)
psi_hist = np.zeros(T)
dphi1_hist = np.zeros(T)
dphi2_hist = np.zeros(T)
for t in range(T):
    R, psi = complex_order_parameter(phi[:, t])
    R_hist[t] = R
    psi_hist[t] = psi
    dphi1_hist[t] = phi[0, t] - phi[2, t]
    dphi2_hist[t] = phi[1, t] - phi[2, t]

# --- Construct phase-space data matrix ---
X = np.vstack([dphi1_hist, dphi2_hist, R_hist]).T

# --- PCA projection to 2D ---
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)
explained = pca.explained_variance_ratio_

# --- Visualization ---
plt.figure(figsize=(7,6))
cmap = plt.cm.plasma
colors = cmap(np.linspace(0, 1, T))

plt.scatter(X_pca[:,0], X_pca[:,1], c=colors, s=6, alpha=0.7, edgecolors='none')
plt.scatter(X_pca[-1,0], X_pca[-1,1], c='black', s=60, label='Final Equilibrium')
plt.title("P10q - Global Resonance Phase-Space Projection")
plt.xlabel(f"PC1 ({explained[0]*100:.1f}% variance)")
plt.ylabel(f"PC2 ({explained[1]*100:.1f}% variance)")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P10q_PhaseSpaceProjection.png", dpi=240)
plt.close()

# --- Save summary ---
results = {
    "eta": eta,
    "noise": noise,
    "K_field": K_field,
    "K_global": K_global,
    "alignment": alignment,
    "metrics": {
        "R_final": float(R_hist[-1]),
        "mean_R": float(np.mean(R_hist[-200:])),
        "pca_explained_variance": [float(v) for v in explained]
    },
    "files": {"projection_plot": "PAEV_P10q_PhaseSpaceProjection.png"},
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P10q_phase_space_projection.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== P10q - Global Resonance Phase-Space Projection ===")
print(f"Final R={results['metrics']['R_final']:.4f}, Mean R={results['metrics']['mean_R']:.4f}")
print(f"Explained variance: {explained[0]*100:.1f}% + {explained[1]*100:.1f}%")
print("✅ Results saved -> backend/modules/knowledge/P10q_phase_space_projection.json")