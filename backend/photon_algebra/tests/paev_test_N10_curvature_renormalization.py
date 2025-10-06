# backend/photon_algebra/tests/paev_test_N10_curvature_renormalization.py

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def main():
    print("=== N10 — Curvature Renormalization Map ===")

    ħ = 1e-3
    G = 1e-5
    Λ0 = 1e-6
    α = 0.5

    # Feedback constant (tunable)
    β = 0.2  # feedback strength
    Rc = 1.0  # critical curvature (normalized)
    
    t = np.linspace(0, 10, 500)
    
    # Simulated curvature and energy densities (toy model)
    R = np.exp(0.3 * np.sin(t)) + 0.02 * np.random.randn(len(t))
    E = np.exp(-0.2 * np.sin(t)) + 0.02 * np.random.randn(len(t))
    
    # Dynamic Λ(t) feedback
    Λ_t = Λ0 * (1 - β * R / Rc)
    
    # Renormalized curvature-energy ratio
    Xi = (R / E) * np.exp(-β * R / Rc)
    
    mean_Xi = np.mean(Xi)
    
    # Classification
    if np.allclose(mean_Xi, 1, rtol=0.1):
        classification = "Stable (self-renormalized)"
    elif mean_Xi < 1:
        classification = "Overdamped (energy-dominant)"
    else:
        classification = "Runaway curvature"
    
    print(f"ħ={ħ:.3e}, G={G:.3e}, Λ₀={Λ0:.3e}, α={α:.3f}, β={β:.2f}")
    print(f"Mean curvature-energy ratio = {mean_Xi:.3e}")
    print(f"Classification: {classification}")
    
    # --- Plot 1: Curvature-Energy Ratio over time ---
    plt.figure(figsize=(8,5))
    plt.plot(t, Xi, color='blue', label='Ξ(t) — Renormalized Ratio')
    plt.axhline(1, color='gray', linestyle='--', label='Equilibrium (Ξ=1)')
    plt.title("N10 — Curvature Renormalization Stability")
    plt.xlabel("Time")
    plt.ylabel("Ξ(t) = (R/E)·exp(-βR/Rc)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("PAEV_N10_CurvatureRenormalization.png")

    # --- Plot 2: Λ feedback map ---
    plt.figure(figsize=(8,5))
    plt.plot(t, Λ_t / Λ0, color='purple', label='Λ(t)/Λ₀ — Feedback Response')
    plt.axhline(1, color='gray', linestyle=':', label='Baseline')
    plt.title("N10 — Λ(t) Feedback Damping Map")
    plt.xlabel("Time")
    plt.ylabel("Λ(t)/Λ₀ (relative)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("PAEV_N10_LambdaFeedback.png")
    
    # Save results
    summary = {
        "ħ": ħ,
        "G": G,
        "Λ0": Λ0,
        "α": α,
        "β": β,
        "mean_Xi": mean_Xi,
        "classification": classification,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    }

    import json, os
    outpath = "backend/modules/knowledge/N10_renormalization_summary.json"
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w") as f:
        json.dump(summary, f, indent=2)
    
    print("✅ Plots saved:")
    print("   - PAEV_N10_CurvatureRenormalization.png")
    print("   - PAEV_N10_LambdaFeedback.png")
    print("📄 Summary:", outpath)
    print("----------------------------------------------------------")

if __name__ == "__main__":
    main()