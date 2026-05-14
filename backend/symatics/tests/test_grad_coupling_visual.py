# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.6 - Visualization: λ↔ψ Coupling Dynamics
# Produces Figure 3 for Volume VII specification.
# ──────────────────────────────────────────────────────────────

import os
import time
import numpy as np
import matplotlib.pyplot as plt

from backend.symatics.core.resonant_laws import ResonantContext
from backend.symatics.core.grad_operators import update_resonant_field
from backend.symatics.core.wave_diff_engine import WaveDiffEngine
from backend.modules.codex.codex_render import CodexRender, record_event

# ──────────────────────────────────────────────────────────────
# Setup simulation
# ──────────────────────────────────────────────────────────────
ctx = ResonantContext()
engine = WaveDiffEngine()
renderer = CodexRender()

# Initial ψ (1D sine wave) and λ (uniform)
ψ0 = np.sin(np.linspace(0, np.pi, 128))
λ0 = np.ones_like(ψ0)

engine.register_field("ψ", ψ0)
engine.register_field("λ", λ0)

energy_trace, coherence_trace, lambda_trace = [], [], []

# ──────────────────────────────────────────────────────────────
# Simulation loop - coupled evolution
# ──────────────────────────────────────────────────────────────
for t in range(150):
    ψ_prev = engine.fields["ψ"].copy()
    energy_prev = np.sum(ψ_prev ** 2)
    coherence_prev = np.exp(-np.linalg.norm(np.gradient(ψ_prev)))

    engine.step("ψ", λ_name="λ", dt=0.1)
    ψ_next = engine.fields["ψ"].copy()
    energy_next = np.sum(ψ_next ** 2)
    coherence_next = np.exp(-np.linalg.norm(np.gradient(ψ_next)))

    # Resonant λ update
    new_λ = update_resonant_field(
        ctx, "resonance_continuity",
        {"energy": energy_prev, "phase": 0.0},
        {"energy": energy_next, "phase": 0.1}
    )

    lambda_trace.append(new_λ)
    energy_trace.append(energy_next)
    coherence_trace.append(coherence_next)

    # Telemetry log
    record_event("wave_energy", value=float(energy_next))
    record_event("coherence_index", value=float(coherence_next))
    record_event("resonant_weight_update", new_weight=float(new_λ))
    time.sleep(0.01)

# ──────────────────────────────────────────────────────────────
# Visualization using CodexRender or fallback
# ──────────────────────────────────────────────────────────────
renderer.ingest()
output_dir = "docs/figures"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "resonant_coupling_dynamics.png")

fig, ax = plt.subplots(3, 1, figsize=(8, 8))
plt.subplots_adjust(hspace=0.4)

t = np.arange(len(lambda_trace))
ax[0].plot(t, lambda_trace, label="λ(t)", color="tab:blue")
ax[1].plot(t, energy_trace, label="E(t)", color="tab:green")
ax[2].plot(t, coherence_trace, label="C(t)", color="tab:orange")

for a in ax:
    a.legend(); a.grid(True, alpha=0.3)
    a.set_xlabel("timestep")

ax[0].set_ylabel("λ")
ax[1].set_ylabel("Energy")
ax[2].set_ylabel("Coherence")

fig.suptitle("Tessaris Symatics - Resonant Coupling Dynamics (λ↔ψ↔E↔C)", fontsize=12)
plt.savefig(output_path, dpi=200)
plt.close(fig)

print(f"✅ Saved {output_path}")
print("🎨 Visualization complete - ready for Volume VII Figure Set.")