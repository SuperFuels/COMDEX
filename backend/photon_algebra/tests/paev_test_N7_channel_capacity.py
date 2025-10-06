#!/usr/bin/env python3
"""
PAEV Test — N7: Quantum Channel Capacity vs Noise
Models how much entanglement-encoded information can survive
as environmental noise increases.
"""

import numpy as np
import matplotlib.pyplot as plt
import json
from math import erf, log2
from datetime import datetime

# ------------------------------------------------------------
# Constants — consistent with prior tests
# ------------------------------------------------------------
ħ = 1e-3
G = 1e-5
Λ = 1e-6
α = 0.5

# ------------------------------------------------------------
# Core Simulation
# ------------------------------------------------------------
def shannon_capacity(snr):
    """Classical Shannon capacity (bits per channel use)"""
    return np.log2(1 + snr)

def quantum_capacity(fidelity):
    """Approximate quantum channel capacity from fidelity"""
    # Use coherent information proxy Q ≈ log2(2F - 1) when F > 0.5
    F = np.clip(fidelity, 0.5, 1.0)
    return np.log2(2 * F - 1)

def main():
    print("=== N7 — Channel Capacity vs Noise ===")
    print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")

    # Noise range (log spaced)
    sigmas = np.logspace(-5, -1, 20)

    # Error probability model using erf
    k = 5.0  # sensitivity factor
    p_err = 0.5 * (1 + np.array([erf(k * s) for s in sigmas])) - 0.5

    # Effective fidelity and SNR
    fidelities = 1 - p_err
    snr = 1 / (sigmas + 1e-9)

    # Channel capacities
    classical_capacity = shannon_capacity(snr)
    quantum_capacity_bits = quantum_capacity(fidelities)

    # ------------------------------------------------------------
    # Results summary
    # ------------------------------------------------------------
    idx_90 = np.argmin(np.abs(fidelities - 0.9))
    sigma_90 = sigmas[idx_90]

    print(f"90% fidelity noise σ ≈ {sigma_90:.3e}")
    print("✅ Plots saved: PAEV_N7_ChannelCapacity.png")

    summary = {
        "ħ": ħ,
        "G": G,
        "Λ": Λ,
        "α": α,
        "sigmas": sigmas.tolist(),
        "fidelities": fidelities.tolist(),
        "classical_capacity": classical_capacity.tolist(),
        "quantum_capacity": quantum_capacity_bits.tolist(),
        "sigma_at_90pct": float(sigma_90),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
    }

    # ------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------
    plt.figure(figsize=(8, 5))
    plt.semilogx(sigmas, classical_capacity, 'r--', label='Classical Capacity log₂(1+SNR)')
    plt.semilogx(sigmas, quantum_capacity_bits, 'b-', label='Quantum Capacity log₂(2F−1)')
    plt.axvline(sigma_90, color='gray', linestyle=':', label=f'σ₉₀={sigma_90:.2e}')
    plt.axhline(0, color='black', lw=0.5)
    plt.xlabel("Noise σ (standard deviation)")
    plt.ylabel("Channel Capacity (bits/use)")
    plt.title("N7 — Channel Capacity vs Noise")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("PAEV_N7_ChannelCapacity.png", dpi=200)

    # Save results JSON
    with open("backend/modules/knowledge/N7_capacity_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("📄 Summary: backend/modules/knowledge/N7_capacity_summary.json")
    print("----------------------------------------------------------")

if __name__ == "__main__":
    main()