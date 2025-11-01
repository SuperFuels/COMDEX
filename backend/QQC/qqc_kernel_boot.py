# ==========================================================
#  Tessaris * Quantum Quad Core (QQC) Boot Harness
#  Environment-driven runtime loader and orchestrator.
# ==========================================================

import asyncio
import logging
import time
import yaml

# Load global configuration & environment
from backend.config import QQC_CONFIG_PATH, QQC_MODE, QQC_AUTO_START, load_qqc_config
from backend.QQC.qqc_kernel_v2 import QuantumQuadCore  # make sure your v2 kernel is imported here

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Initializing Tessaris Quantum Quad Core (QQC) Runtime...")

    # Load the global QQC configuration
    cfg = load_qqc_config()
    if not cfg:
        logger.warning(f"[QQC Boot] ⚠️ Could not load config from {QQC_CONFIG_PATH}, using defaults.")

    # Instantiate the core
    qqc = QuantumQuadCore()

    # Auto-boot if enabled
    if QQC_AUTO_START:
        boot_mode = QQC_MODE or cfg.get("boot", {}).get("mode", "resonant")
        logger.info(f"[QQC Boot] Starting QQC in mode='{boot_mode}'")
        await qqc.boot(mode=boot_mode)
    else:
        logger.info("[QQC Boot] Auto-start disabled by configuration. Waiting for manual trigger...")

    # Simulated LightWave test cycles
    for i in range(5):
        beam_data = {
            "beam_id": f"ψ_{i}",
            "coherence": 0.7 + 0.05 * i,
            "phase_shift": 0.01 * i,
            "entropy_drift": 0.02 * (i - 2),
            "gain": 1.0 + 0.1 * i,
            "timestamp": time.time(),
        }
        await qqc.run_cycle(beam_data)

    await qqc.broadcast_kernel_state()

    print("\n🧭 Final QQC Summary:")
    print(qqc.last_summary)

    # Optional shutdown hook
    await qqc.shutdown()
    logger.info("✅ Quantum Quad Core shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 QQC Kernel manually stopped.")