# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.7 — Visualization Generator
# Figure: λ–ψ Symbolic Fluid Topology (Field Flow)
# Output: docs/figures/field_flow_topology.png
# ──────────────────────────────────────────────────────────────

import os
import numpy as np
import matplotlib.pyplot as plt
from backend.symatics.core.field_coupling_engine import FieldCouplingEngine
from backend.symatics.core.flow_operators import coherence_flux, divergence, laplacian

# Ensure figure directory exists
os.makedirs("docs/figures", exist_ok=True)

# ──────────────────────────────────────────────────────────────
# Initialize symbolic fields
engine = FieldCouplingEngine(viscosity=0.02, damping=0.01, eta=0.05)
x = np.linspace(0, np.pi, 128)
ψ0 = np.sin(x)
λ0 = np.ones_like(ψ0)

engine.register_field("ψ", ψ0)
engine.register_field("λ", λ0)

# ──────────────────────────────────────────────────────────────
# Simulation loop
frames = 80
ψ_hist, λ_hist = [], []

for t in range(frames):
    ψ, λ = engine.step("ψ", "λ", dt=0.1)
    ψ_hist.append(ψ.copy())
    λ_hist.append(λ.copy())

ψ_final = ψ_hist[-1]
λ_final = λ_hist[-1]
Φ = coherence_flux(ψ_final)
divψ = divergence(ψ_final)
lapψ = laplacian(ψ_final)

# ──────────────────────────────────────────────────────────────
# Visualization
plt.figure(figsize=(10, 5))
plt.suptitle("Tessaris Symatics — λ–ψ Symbolic Field Flow (v0.7)", fontsize=14)

# Coherence coloration field
plt.subplot(1, 1, 1)
plt.title("Symbolic Fluid Topology: λ↔ψ Coupling with Coherence Flux", fontsize=12)
plt.xlabel("Position (x)")
plt.ylabel("Amplitude")

# Color map for coherence flux (Φ)
colors = plt.cm.viridis((Φ - Φ.min()) / (Φ.max() - Φ.min()))

plt.plot(x, ψ_final, color="white", linewidth=1.5, label="ψ (wave)")
plt.fill_between(x, ψ_final, color="gray", alpha=0.2)
plt.scatter(x, λ_final, c=colors, s=15, label="λ (law field)", zorder=5)

plt.text(
    np.pi * 0.5,
    0.9,
    "λ(t) follows ∇·ψ feedback\ncoherence flux Φ stabilizes oscillation",
    ha="center",
    fontsize=9,
    color="dimgray",
)

plt.legend(loc="upper right", fontsize=9)
plt.grid(alpha=0.2)
plt.tight_layout()

# Save figure
out_path = "docs/figures/field_flow_topology.png"
plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")

print(f"✅ Saved {out_path}")
print("🎨 λ–ψ symbolic fluid flow visualization complete — ready for Volume VIII.")