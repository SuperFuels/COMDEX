# ──────────────────────────────────────────────────────────────
# Tessaris CodexRender — Visualization Demo
# Simulates λ(t), ψ(t), and E(t) evolution in real time.
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v1.2.0 — October 2025
# ──────────────────────────────────────────────────────────────

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import numpy as np
import time
from datetime import datetime
from backend.modules.codex.codex_render import CodexRender, record_event

# ──────────────────────────────────────────────────────────────
# Initialize visualization engine
# ──────────────────────────────────────────────────────────────
renderer = CodexRender()

# Simulate ~100 telemetry events (λ, ψ-energy, coherence)
for t in range(100):
    λ = 0.8 + 0.2 * np.sin(t / 10)
    E = 1.0 - 0.005 * t + 0.05 * np.cos(t / 15)
    C = np.exp(-0.01 * t) + 0.02 * np.random.randn()

    # Emit Codex telemetry events
    record_event("law_weight_update", new_weight=λ)
    record_event("wave_energy", value=E)
    record_event("coherence_index", value=C)

    time.sleep(0.05)  # simulate runtime pacing

# ──────────────────────────────────────────────────────────────
# Aggregate & render λ–ψ–E feedback visualization
# ──────────────────────────────────────────────────────────────
renderer.ingest()

# Create output directory
output_dir = os.path.join("docs", "figures")
os.makedirs(output_dir, exist_ok=True)

# Build filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(output_dir, f"lambda_psi_energy_feedback_{timestamp}.png")

# Render and save figure
renderer.plot(show=False, save_path=output_path)

# ──────────────────────────────────────────────────────────────
# Summary output
# ──────────────────────────────────────────────────────────────
print(f"✅ Visualization saved to {output_path}")
if hasattr(renderer, "buffer"):
    print("Last 5 telemetry events:")
    print(renderer.buffer[-5:])
else:
    print("⚠️ No telemetry buffer found — check CodexRender configuration.")