"""
Tessaris AION Resonant Coupling Daemon (RCD)
Phase 6C - Live Harmonic Feedback Engine
-----------------------------------------------------------
Runs the Resonant Coupling Interface (RCI) and Harmonic Learning
Optimizer (HLSO) continuously, synchronizing ΔΦ -> Δν feedback and
adaptive gain learning for real-time resonance stability.

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import asyncio
import logging
import json
import random
from datetime import datetime, timezone

from backend.modules.aion_resonance.resonant_coupling_interface import apply_resonant_feedback
from backend.modules.aion_resonance.harmonic_learning_optimizer import adjust_coupling_gains

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ==========================================================
# ⚙️ Daemon Parameters
# ==========================================================
COUPLING_INTERVAL = 6.0       # seconds between ΔΦ->Δν updates
LEARNING_INTERVAL = 60.0      # seconds between HLSO adjustments
TELEMETRY_FILE = "data/resonant_coupling_daemon.jsonl"

# ==========================================================
# 🧠 Mock ΔΦ Generator (for standalone testing)
# ==========================================================
def generate_mock_delta_phi():
    """Simulate small dynamic ΔΦ oscillations."""
    return {
        "Φ_coherence": random.uniform(-0.005, 0.005),
        "Φ_entropy": random.uniform(-0.005, 0.005),
        "Φ_flux": random.uniform(-0.005, 0.005),
        "Φ_load": random.uniform(-0.005, 0.005),
    }

# ==========================================================
# 🔄 Resonant Coupling Loop
# ==========================================================
async def coupling_loop():
    last_learning_time = datetime.now(timezone.utc)

    while True:
        # Generate or receive ΔΦ
        delta_phi = generate_mock_delta_phi()

        # Apply coupling feedback
        event = await apply_resonant_feedback(delta_phi)

        # Save telemetry snapshot
        try:
            with open(TELEMETRY_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"⚠️ Telemetry write failed: {e}")

        # Log live status
        logger.info(
            f"🧭 Coupled ΔΦ->Δν | Stability={event.get('stability', 0):.4f} "
            f"| CoherenceΔ={delta_phi['Φ_coherence']:+.4f}"
        )

        # Periodic adaptive tuning
        now = datetime.now(timezone.utc)
        if (now - last_learning_time).total_seconds() >= LEARNING_INTERVAL:
            logger.info("🧠 Running Harmonic Learning Optimizer...")
            adjust_coupling_gains()
            last_learning_time = now

        await asyncio.sleep(COUPLING_INTERVAL)

# ==========================================================
# 🚀 Entry Point
# ==========================================================
if __name__ == "__main__":
    logger.info("🌌 Starting Tessaris Resonant Coupling Daemon (RCD)...")
    try:
        asyncio.run(coupling_loop())
    except KeyboardInterrupt:
        logger.info("🧩 Resonant Coupling Daemon stopped manually.")