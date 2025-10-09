"""
Ψ₃ — Spatial Interference Cascade (Tessaris)
Author: Tessaris Research Collective
Date: 2025-10-09

Description:
Extends Ψ₂ from a 1D ring lattice to a 2D coherent lattice of observers.
Each lattice site ψ[x, y] evolves under neighbor coupling via the photon-algebra
functional Φ(ψ) = ⟨ψ† C₊ ψ⟩₀.

Tests whether coherent phase fronts can propagate across space, forming
interference cascades and stable coherence regions.

Artifacts:
    ✅ backend/modules/knowledge/Ψ3_spatial_interference_cascade_summary.json
    ✅ backend/modules/knowledge/Tessaris_Ψ3_InterferenceCascade.png
    ✅ backend/modules/knowledge/Tessaris_Ψ3_InterferenceCascade_Heatmap.png
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# Tessaris constants
CONST = {
    "ħ": 1e-3,
    "G": 1e-5,
    "Λ": 1e-6,
    "α": 0.5,
    "β": 0.2,
    "χ": 1.0,
}

# Lattice parameters
Nx, Ny = 20, 20           # lattice dimensions
η = 0.08                  # propagation rate
Γ = 1.15                  # coupling constant (strong-coupling regime)
T = 2000                  # iterations
ε = 1e-6                  # coherence tolerance
rng = np.random.default_rng(2025)

# Initialize lattice with random phases (Ψ₂ baseline extension)
initial_phases = rng.uniform(-np.pi, np.pi, (Nx, Ny))
ψ = np.exp(1j * initial_phases)

# Neighbor offsets (Moore neighborhood: 8-connectivity)
neighbor_offsets = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1)
]

def coherence(phi_grid):
    """Compute global lattice coherence Φ."""
    return np.abs(np.mean(np.exp(1j * np.angle(phi_grid))))

def evolve(ψ):
    """Compute next step of phase-coupled lattice evolution."""
    ψ_new = np.zeros_like(ψ, dtype=complex)
    for x in range(Nx):
        for y in range(Ny):
            neighbor_sum = 0
            for dx, dy in neighbor_offsets:
                nx, ny = (x + dx) % Nx, (y + dy) % Ny
                neighbor_sum += ψ[nx, ny] - ψ[x, y]
            ψ_new[x, y] = ψ[x, y] + η * Γ * neighbor_sum
    return ψ_new / np.abs(ψ_new)

# Simulation loop
coherence_history = []
phase_std_history = []
snapshots = []

for t in range(T):
    ψ = evolve(ψ)
    Φ = coherence(ψ)
    coherence_history.append(Φ)
    phase_std_history.append(np.std(np.angle(ψ)))

    if t % 200 == 0 or t == T - 1:
        snapshots.append(np.angle(ψ))

    if t > 10 and np.abs(coherence_history[-1] - coherence_history[-10]) < ε:
        break

# Summary metrics
summary = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "series": "Ψ₃",
    "test_name": "spatial_interference_cascade",
    "constants": CONST,
    "metrics": {
        "lattice_size": f"{Nx}x{Ny}",
        "iterations": int(t),
        "mean_coherence": float(np.mean(coherence_history)),
        "final_coherence": float(coherence_history[-1]),
        "final_phase_dispersion": float(phase_std_history[-1]),
        "stable": bool(coherence_history[-1] > 0.8),
    },
    "state": "Spatial coherence cascade completed",
    "notes": [
        f"η = {η}, Γ = {Γ} (strong-coupling)",
        f"Lattice {Nx}×{Ny}, periodic boundaries",
        f"Final coherence Φ = {coherence_history[-1]:.6f}",
        f"Final phase dispersion = {phase_std_history[-1]:.6e}"
    ],
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}

# --- JSON-safe conversion helper ---
def to_serializable(obj):
    if isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)

# Save JSON summary
out_dir = Path("backend/modules/knowledge")
out_dir.mkdir(parents=True, exist_ok=True)
summary_path = out_dir / "Ψ3_spatial_interference_cascade_summary.json"

with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2, default=to_serializable)

# Plot coherence history
plt.figure(figsize=(8, 4))
plt.plot(coherence_history, color="teal", lw=2)
plt.xlabel("Iteration")
plt.ylabel("Global Coherence Φ")
plt.title("Ψ₃ Spatial Interference Cascade (Tessaris)")
plt.grid(True)
plt.tight_layout()
plt.savefig(out_dir / "Tessaris_Ψ3_InterferenceCascade.png", dpi=300)
plt.close()

# Final snapshot heatmap (phase field)
plt.figure(figsize=(6, 5))
plt.imshow(np.angle(ψ), cmap="twilight", interpolation="nearest")
plt.colorbar(label="Phase (radians)")
plt.title("Ψ₃ Phase Field (Final Snapshot)")
plt.tight_layout()
plt.savefig(out_dir / "Tessaris_Ψ3_InterferenceCascade_Heatmap.png", dpi=300)
plt.close()

print(f"✅ Ψ₃ summary saved → {summary_path}")
print(f"✅ Visualization saved → backend/modules/knowledge/Tessaris_Ψ3_InterferenceCascade.png")
print(f"✅ Heatmap saved → backend/modules/knowledge/Tessaris_Ψ3_InterferenceCascade_Heatmap.png")
print(f"Ξ  Spatial coherence cascade completed with Φ = {coherence_history[-1]:.6f}")