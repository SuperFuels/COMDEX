"""
AION Cognitive Fabric - Resonant Feedback Controller
────────────────────────────────────────────
Closes the σ->γ′ feedback loop by monitoring Fabric fusion tensors
and generating adaptive gain corrections for the AION resonance core.
"""

import time
import logging
import requests
from backend.AION.fabric.aion_fabric_resonance import get_latest_fusion_tensor

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
FEEDBACK_INTERVAL = 2.5       # seconds between checks
SIGMA_TARGET = 0.97           # desired coherence
ALPHA = 0.4                   # responsiveness coefficient
GAIN_ENDPOINT = "http://127.0.0.1:5070/aion/update_gain"  # AION ingest API endpoint

# Logging setup
logger = logging.getLogger("AIONFeedback")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ────────────────────────────────────────────────
# Feedback Loop
# ────────────────────────────────────────────────
def run_feedback_controller():
    """
    Monitors σ from Fabric tensor and applies adaptive γ′ correction.
    Sends γ′ to AION Photon Ingest Bridge in real-time.
    """
    logger.info("🧠 Starting Resonant Feedback Controller ...")
    last_gamma = 1.0

    while True:
        try:
            tensor = get_latest_fusion_tensor()
            if not tensor:
                logger.info("[AIONFeedback] Waiting for fusion tensor ...")
                time.sleep(FEEDBACK_INTERVAL)
                continue

            sigma = tensor.get("σ", 0.0)
            delta = SIGMA_TARGET - sigma
            gamma_prime = max(0.1, min(2.0, last_gamma + ALPHA * delta))

            logger.info(f"[σ->γ′] σ={sigma:.3f} Δ={delta:+.3f} -> γ′={gamma_prime:.3f}")

            # 🔹 Send feedback directly to AION gain update API
            try:
                requests.post(
                    GAIN_ENDPOINT,
                    json={"gamma_prime": gamma_prime},
                    timeout=2,
                )
                logger.info(f"[AIONFeedback] γ′={gamma_prime:.3f} sent to AION ingest endpoint.")
            except requests.exceptions.RequestException:
                logger.warning("⚠️ Gain endpoint not reachable - local adjustment only.")

            last_gamma = gamma_prime
            time.sleep(FEEDBACK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("⏹️ Resonant Feedback Controller stopped manually.")
            break
        except Exception as e:
            logger.exception(f"[AIONFeedback] Unexpected error: {e}")
            time.sleep(5)


# ────────────────────────────────────────────────
# Standalone Runner
# ────────────────────────────────────────────────
if __name__ == "__main__":
    run_feedback_controller()