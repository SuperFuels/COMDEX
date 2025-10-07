# -*- coding: utf-8 -*-
"""
F17 — Quantum Domain Coupling Test
----------------------------------
Purpose:
  • Test if independent Λ-domains with similar Λ_eff spontaneously synchronize
    via curvature coupling (nonlocal information linkage).
  • Confirms whether multiverse-like domains communicate through shared vacuum curvature.

Core Model:
    dΛ_i/dt = γ * (ΔS_i - ΔE_i) - ζ (Λ_i - Λ_eq) + η * Σ_j w_ij (Λ_j - Λ_i)

Parameters:
  γ — proportional feedback gain
  ζ — damping to equilibrium Λ_eq
  η — inter-domain coupling strength
  w_ij — normalized adjacency weights between domains

Outputs:
  - PAEV_F17_LambdaDomains.png
  - PAEV_F17_SynchronizationIndex.png
  - backend/modules/knowledge/F17_quantum_domain_coupling.json
"""
from pathlib import Path
from datetime import datetime, timezone
import numpy as np, matplotlib.pyplot as plt, json

# --- Constants ---
ħ, G, α, Λ0 = 1e-3, 1e-5, 0.5, 1e-6
T, dt = 3000, 0.006
t = np.arange(T) * dt

# --- Parameters ---
N = 5                    # number of domains
γ = 0.004
ζ = 0.9
η = 0.015
Λ_eq = Λ0
Λ = np.zeros((N, T)); Λ[:, 0] = Λ0 * (1 + 0.05*np.random.randn(N))

# Domain weights (complete graph, normalized)
W = np.ones((N, N)) - np.eye(N)
W /= W.sum(axis=1, keepdims=True)

# Synthetic entropy/energy fields
E = 0.1*np.sin(0.4*t) + 0.05*np.cos(0.23*t)
S = 0.7 + 0.05*np.sin(0.18*t + 0.5)

# --- Evolution ---
for k in range(1, T):
    ΔS = S[k] - S[k-1]
    ΔE = E[k] - E[k-1]
    for i in range(N):
        coupling = np.sum(W[i] * (Λ[:, k-1] - Λ[i, k-1]))
        dΛ = γ * (ΔS - ΔE) - ζ*(Λ[i, k-1] - Λ_eq) + η * coupling
        Λ[i, k] = Λ[i, k-1] + dt*dΛ

# --- Synchronization Metric ---
Λ_mean = Λ.mean(axis=0)
sync_index = 1 - np.std(Λ - Λ_mean, axis=0) / np.mean(np.abs(Λ_mean) + 1e-9)

# --- Diagnostics ---
final_drift = float(np.mean(Λ[:, -1] - Λ_eq))
sync_final = float(np.mean(sync_index[-300:]))
classification = (
    "✅ Domains synchronized (quantum curvature coherence)"
    if sync_final > 0.98 else
    "⚠️ Partial synchronization (weak coupling)"
)

print("=== F17 — Quantum Domain Coupling Test ===")
print(f"N={N}, γ={γ:.3f}, ζ={ζ:.2f}, η={η:.3f}")
print(f"Final sync index={sync_final:.3f}, Λ_drift={final_drift:.3e}")
print(f"→ {classification}")

# --- Plots ---
out = Path(".")
plt.figure(figsize=(10,5))
for i in range(N):
    plt.plot(t, Λ[i], lw=1.2, label=f"Domain {i+1}")
plt.title("F17 — Λ Evolution in Coupled Quantum Domains")
plt.xlabel("time"); plt.ylabel("Λ_i(t)"); plt.legend(); plt.tight_layout()
plt.savefig(out/"PAEV_F17_LambdaDomains.png", dpi=160)

plt.figure(figsize=(8,4))
plt.plot(t, sync_index, lw=1.6, color='purple')
plt.title("F17 — Domain Synchronization Index")
plt.xlabel("time"); plt.ylabel("Synchronization (1 - σ/μ)")
plt.tight_layout(); plt.savefig(out/"PAEV_F17_SynchronizationIndex.png", dpi=160)

print("✅ Plots saved:")
print("  - PAEV_F17_LambdaDomains.png")
print("  - PAEV_F17_SynchronizationIndex.png")

# --- Knowledge Card ---
summary = {
    "ħ": ħ, "G": G, "α": α, "Λ0": Λ0,
    "γ": γ, "ζ": ζ, "η": η, "N": N,
    "timing": {"steps": T, "dt": dt},
    "metrics": {"sync_final": sync_final, "Λ_drift": final_drift},
    "classification": classification,
    "files": {
        "lambda_domains": "PAEV_F17_LambdaDomains.png",
        "sync_plot": "PAEV_F17_SynchronizationIndex.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge/F17_quantum_domain_coupling.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/F17_quantum_domain_coupling.json")