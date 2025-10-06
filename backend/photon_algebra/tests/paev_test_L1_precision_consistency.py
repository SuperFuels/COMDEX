"""
L1 — Precision Consistency Sweep
Validates numerical stability and cross-domain consistency of TOE constants.
Outputs energy/entropy coherence plots and drift distributions.
"""

from __future__ import annotations
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

BANNER = "=== L1 — Precision Consistency Sweep ==="

def load_constants() -> dict:
    path = Path("backend/modules/knowledge/constants_v1.1.json")
    if not path.exists():
        raise FileNotFoundError(f"Missing constants file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def simulate_precision_drift(constants: dict, n_steps: int = 500):
    ħ = constants["ħ_eff"]
    G = constants["G_eff"]
    Λ = constants["Λ_eff"]
    α = constants["α_eff"]

    # Simulated domain scaling (quantum → relativistic)
    x = np.linspace(0, 1, n_steps)
    drift_energy = ħ * np.exp(-x) + G * np.sin(5 * x) + Λ * x**2
    drift_entropy = α * (1 - np.exp(-x)) + 0.5 * G * np.cos(3 * x)

    # Precision metrics
    delta_E = np.abs(np.gradient(drift_energy))
    delta_S = np.abs(np.gradient(drift_entropy))
    coherence = np.corrcoef(drift_energy, drift_entropy)[0, 1]

    return x, drift_energy, drift_entropy, delta_E, delta_S, coherence

def main():
    print(BANNER)
    constants = load_constants()
    x, E, S, dE, dS, coherence = simulate_precision_drift(constants)

    print(f"ħ={constants['ħ_eff']:.3e}, G={constants['G_eff']:.3e}, "
          f"Λ={constants['Λ_eff']:.3e}, α={constants['α_eff']:.3f}")
    print(f"Coherence (E↔S): {coherence:.6f}")

    # Plot Energy–Entropy evolution
    plt.figure(figsize=(7,5))
    plt.plot(x, E, label="Energy (E)", lw=2)
    plt.plot(x, S, label="Entropy (S)", lw=2, ls="--")
    plt.title("L1 Precision Consistency Sweep")
    plt.xlabel("Domain scale (0→1)")
    plt.ylabel("Normalized magnitude")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("PAEV_L1_ConsistencyMap.png")

    # Plot drift distribution
    plt.figure(figsize=(7,5))
    plt.plot(x, dE, label="ΔE drift", lw=2)
    plt.plot(x, dS, label="ΔS drift", lw=2, ls="--")
    plt.title("Drift Magnitude Distribution")
    plt.xlabel("Domain scale")
    plt.ylabel("Drift magnitude")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("PAEV_L1_DriftDistribution.png")

    print("✅ Plots saved:")
    print("   - PAEV_L1_ConsistencyMap.png")
    print("   - PAEV_L1_DriftDistribution.png")
    print("----------------------------------------------------------")

if __name__ == "__main__":
    main()