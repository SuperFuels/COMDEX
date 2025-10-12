# backend/symatics/tests/gen_figures_tensor_field.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.8 — Tensor Field Visualization Script
# Generates docs/figures/tensor_resonance_manifold.png
# Visualizes λ⊗ψ resonance manifold and coherence flux.
# ──────────────────────────────────────────────────────────────

import numpy as np
import matplotlib.pyplot as plt
from backend.symatics.core.tensor_field_engine import ResonantTensorField

def generate_tensor_resonance_figure():
    # Initialize tensor field
    field = ResonantTensorField(shape=(48, 48))
    ψ, λ = field.ψ, field.λ

    # Run a few evolution steps
    for _ in range(25):
        ψ, λ = field.step(dt=0.05)

    # Compute coherence flux surface
    coherence = np.exp(-np.linalg.norm(np.gradient(ψ), axis=0))

    # Prepare figure
    fig, ax = plt.subplots(figsize=(7, 6))
    X, Y = np.meshgrid(np.linspace(0, 1, ψ.shape[1]), np.linspace(0, 1, ψ.shape[0]))

    contour = ax.contourf(X, Y, ψ, levels=100, cmap="viridis", alpha=0.85)
    ax.streamplot(X, Y, λ, ψ, color="white", density=0.6, linewidth=0.5)
    ax.set_title("λ⊗ψ Tensor Resonance Manifold", fontsize=13)
    ax.set_xlabel("ψ-domain")
    ax.set_ylabel("λ-domain")

    # Overlay coherence contours
    coh = ax.contour(X, Y, coherence, levels=10, colors="magenta", linewidths=0.7)
    ax.clabel(coh, fmt="%.2f", fontsize=7, colors="magenta")

    # Save figure
    plt.tight_layout()
    output_path = "docs/figures/tensor_resonance_manifold.png"
    plt.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"✅ Saved {output_path}")
    print("🎨 Tensor resonance manifold visualization complete — ready for Volume IX.")

if __name__ == "__main__":
    generate_tensor_resonance_figure()