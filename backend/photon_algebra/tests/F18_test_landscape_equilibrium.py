# -*- coding: utf-8 -*-
"""
F18 — Landscape Meta-Equilibrium Test
-------------------------------------
Purpose:
  • Introduce weak inter-domain diffusion to test convergence of Λ_i toward
    a global mean Λ̄ — i.e., meta-equilibrium across a vacuum landscape.
  • Confirms whether multiple vacuum domains reach shared stability.

Core Model:
    dΛ_i/dt = γ (ΔS - ΔE) - ζ (Λ_i - Λ_eq) - κ (Λ_i - Λ̄)

Outputs:
  - PAEV_F18_LandscapeConvergence.png
  - PAEV_F18_DriftHistogram.png
  - backend/modules/knowledge/F18_landscape_equilibrium.json
"""
from pathlib import Path
from datetime import datetime, timezone
import numpy as np, matplotlib.pyplot as plt, json

# --- Constants ---
ħ, G, α, Λ0 = 1e-3, 1e-5, 0.5, 1e-6
T, dt = 3000, 0.006
t = np.arange(T) * dt

# --- Parameters ---
N = 6
γ = 0.004
ζ = 1.0
κ = 0.012
Λ_eq = Λ0
Λ = np.zeros((N, T)); Λ[:, 0] = Λ0 * (1 + 0.2*np.random.randn(N))

E = 0.1*np.sin(0.35*t) + 0.05*np.cos(0.23*t)
S = 0.7 + 0.05*np.sin(0.18*t + 0.9)

# --- Evolution ---
for k in range(1, T):
    ΔS = S[k] - S[k-1]
    ΔE = E[k] - E[k-1]
    Λ_mean = np.mean(Λ[:, k-1])
    for i in range(N):
        dΛ = γ*(ΔS - ΔE) - ζ*(Λ[i, k-1] - Λ_eq) - κ*(Λ[i, k-1] - Λ_mean)
        Λ[i, k] = Λ[i, k-1] + dt*dΛ

# --- Metrics ---
Λ_final = Λ[:, -1]
Λ_spread = float(np.std(Λ_final))
Λ_convergence = 1 - Λ_spread / (np.mean(np.abs(Λ_final)) + 1e-9)
classification = (
    "✅ Meta-equilibrium reached (landscape convergence)"
    if Λ_convergence > 0.98 else
    "⚠️ Partial equilibrium (diffusion insufficient)"
)

print("=== F18 — Landscape Meta-Equilibrium Test ===")
print(f"N={N}, γ={γ:.3f}, ζ={ζ:.2f}, κ={κ:.3f}")
print(f"Λ_convergence={Λ_convergence:.3f}, Λ_spread={Λ_spread:.3e}")
print(f"→ {classification}")

# --- Plots ---
out = Path(".")
plt.figure(figsize=(10,5))
for i in range(N):
    plt.plot(t, Λ[i], lw=1.2, label=f"Domain {i+1}")
plt.title("F18 — Λ Evolution Across Landscape Domains")
plt.xlabel("time"); plt.ylabel("Λ_i(t)"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_F18_LandscapeConvergence.png", dpi=160)

plt.figure(figsize=(6,4))
plt.hist(Λ_final, bins=8, color='gray', alpha=0.7)
plt.title("F18 — Final Λ Distribution Across Domains")
plt.xlabel("Λ_final"); plt.ylabel("count")
plt.tight_layout(); plt.savefig(out/"PAEV_F18_DriftHistogram.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_F18_LandscapeConvergence.png")
print("  - PAEV_F18_DriftHistogram.png")

# --- Knowledge Card ---
summary = {
    "ħ": ħ, "G": G, "α": α, "Λ0": Λ0,
    "γ": γ, "ζ": ζ, "κ": κ, "N": N,
    "timing": {"steps": T, "dt": dt},
    "metrics": {
        "Λ_convergence": Λ_convergence,
        "Λ_spread": Λ_spread
    },
    "classification": classification,
    "files": {
        "landscape_plot": "PAEV_F18_LandscapeConvergence.png",
        "drift_hist": "PAEV_F18_DriftHistogram.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/F18_landscape_equilibrium.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/F18_landscape_equilibrium.json")