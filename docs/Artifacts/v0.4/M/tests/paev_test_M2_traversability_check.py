"""
M2 - Wormhole Traversability Check
Verifies whether entangled curvature wells allow nonlocal correlation 
without classical information transfer (ER=EPR non-traversable wormhole analogue).
"""

import numpy as np
import matplotlib.pyplot as plt
from backend.modules.theory_of_everything.toe_lagrangian import define_lagrangian

def evolve_fields(ψ1, ψ2, κ1, κ2, ħ, G, Λ, α, steps=400, dt=0.01):
    mutual_info = []
    classical_flux = []
    for t in range(steps):
        # Inject a small perturbation into ψ1
        if t == 10:
            ψ1 += np.exp(-((X + 2)**2 + Y**2)) * (0.1j)

        # Compute Laplacians
        lap1 = np.gradient(np.gradient(ψ1, axis=0), axis=0)[0] + np.gradient(np.gradient(ψ1, axis=1), axis=1)[0]
        lap2 = np.gradient(np.gradient(ψ2, axis=0), axis=0)[0] + np.gradient(np.gradient(ψ2, axis=1), axis=1)[0]

        # Update (Schrödinger-like evolution)
        ψ1 = ψ1 + dt * (1j * ħ * lap1 - α * κ1 * ψ1)
        ψ2 = ψ2 + dt * (1j * ħ * lap2 - α * κ2 * ψ2)

        # Mutual information proxy (real correlation)
        corr = np.mean(np.real(ψ1 * np.conj(ψ2)))
        mutual_info.append(corr)

        # Classical flux (field overlap magnitude)
        overlap = np.sum(np.abs(ψ1 - ψ2))
        classical_flux.append(overlap)

    return np.array(mutual_info), np.array(classical_flux)

if __name__ == "__main__":
    print("=== M2 - Wormhole Traversability Check ===")

    # Spatial grid
    x = np.linspace(-5, 5, 200)
    X, Y = np.meshgrid(x, x)
    r1, r2 = np.sqrt((X + 2)**2 + Y**2), np.sqrt((X - 2)**2 + Y**2)

    # Curvature wells
    κ1 = -1.0 / (r1**2 + 1)
    κ2 = -1.0 / (r2**2 + 1)

    # Initialize complex wavefields
    ψ1 = np.exp(-r1**2).astype(np.complex128)
    ψ2 = (np.exp(-r2**2) * np.exp(1j * 0.5)).astype(np.complex128)

    # Constants
    consts = define_lagrangian({
        "E_mean": 0.024, "S_mean": 3.34,
        "psi_kappa_mean": -0.0013, "psi_T_mean": 0.00024
    })
    ħ, G, Λ, α = consts["ħ_eff"], consts["G_eff"], consts["Λ_eff"], consts["α_eff"]

    # Run evolution
    mutual_info, classical_flux = evolve_fields(ψ1, ψ2, κ1, κ2, ħ, G, Λ, α)

    # Plot results
    plt.figure()
    plt.plot(mutual_info, label="Mutual Information I(ψ1; ψ2)")
    plt.plot(classical_flux / np.max(classical_flux), '--', label="Normalized Classical Flux")
    plt.xlabel("Time step")
    plt.ylabel("Correlation / Flux (normalized)")
    plt.title("M2 - Wormhole Traversability Check")
    plt.legend()
    plt.tight_layout()
    plt.savefig("PAEV_M2_Traversability.png")

    # Results summary
    print(f"ΔI = {mutual_info[-1] - mutual_info[0]:.3e}")
    print(f"Classical flux final/initial ratio = {classical_flux[-1]/classical_flux[0]:.3e}")
    if mutual_info[-1] > 1e-3 and classical_flux[-1]/classical_flux[0] < 1.1:
        print("✅ Non-traversable wormhole confirmed (correlation sustained, no classical transfer).")
    else:
        print("⚠️ Traversable behavior detected - review causality conditions.")
    print("✅ Plot saved: PAEV_M2_Traversability.png")
    print("----------------------------------------------------------")