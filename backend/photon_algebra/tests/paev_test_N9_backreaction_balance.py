import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

def main():
    # === Physical constants ===
    ħ = 1e-3       # Reduced Planck constant (scaled)
    G = 1e-5       # Gravitational constant
    Λ = 1e-6       # Cosmological constant
    α = 0.5        # Coupling coefficient

    # === Define ranges ===
    fidelities = np.linspace(0.5, 1.0, 200)
    E_bit = 1.2e14 * (0.9 / fidelities) ** 2  # reuse N8 scaling (Landauer-like)
    curvature = (α / (ħ * G)) * (fidelities - 0.5) ** 2  # proxy for backreaction

    # === Energy balance proxy ===
    balance_ratio = curvature / (E_bit / np.max(E_bit))

    # === Stability classification ===
    mean_balance = np.mean(balance_ratio)
    if 0.9 < mean_balance < 1.1:
        classification = "Balanced (self-sustaining)"
    elif mean_balance >= 1.1:
        classification = "Runaway curvature (collapse)"
    else:
        classification = "Underdriven (unstable)"

    # === Plot ===
    plt.figure(figsize=(8,5))
    plt.plot(fidelities, balance_ratio, label="Energy-Curvature Balance Ratio", color='blue')
    plt.axhline(1.0, color='gray', linestyle='--', label='Equilibrium (1.0)')
    plt.axvline(0.9, color='red', linestyle=':', label='90% fidelity')
    plt.title("N9 - Thermodynamic Backreaction & Energy Balance")
    plt.xlabel("Fidelity |⟨ψ1|ψ2⟩|2")
    plt.ylabel("Curvature / Energy ratio (normalized)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("PAEV_N9_BackreactionBalance.png")

    # === Print summary ===
    print("=== N9 - Thermodynamic Backreaction & Energy Balance ===")
    print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
    print(f"Mean balance ratio = {mean_balance:.3f}")
    print(f"Classification: {classification}")
    print("✅ Plot saved: PAEV_N9_BackreactionBalance.png")

    # === Save summary JSON ===
    result = {
        "ħ": ħ,
        "G": G,
        "Λ": Λ,
        "α": α,
        "mean_balance_ratio": mean_balance,
        "classification": classification,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    }

    with open("backend/modules/knowledge/N9_backreaction_summary.json", "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()