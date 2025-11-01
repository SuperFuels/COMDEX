"""
Photon Bridge Shared Configuration
────────────────────────────────────────────
Centralized runtime configuration for all Photon bridges
(QQC ↔ AION ↔ GHX), ensuring consistent connection
behavior, logging, and retry policies.

Used by:
    - backend/QQC/photon_bridge/qqc_photon_bridge.py
    - backend/AION/photon_bridge/aion_photon_ingest.py
"""

import os
import logging
from dataclasses import dataclass

# ────────────────────────────────────────────────
#  Global Configuration
# ────────────────────────────────────────────────
@dataclass(frozen=True)
class PhotonBridgeConfig:
    """Immutable configuration parameters shared across Photon bridges."""
    sse_url: str = os.getenv("PHOTON_SSE_URL", "http://127.0.0.1:5005/stream/ghx")
    retry_delay: float = float(os.getenv("PHOTON_RETRY_DELAY", "5.0"))
    max_backoff: int = int(os.getenv("PHOTON_MAX_BACKOFF", "5"))
    log_level: str = os.getenv("PHOTON_LOG_LEVEL", "INFO")

# Instantiate singleton config
CONFIG = PhotonBridgeConfig()

# ────────────────────────────────────────────────
#  Logger Utility
# ────────────────────────────────────────────────
def init_bridge_logger(name: str) -> logging.Logger:
    """Initialize a standardized logger for Photon bridges."""
    logger = logging.getLogger(name)
    level = getattr(logging, CONFIG.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# ────────────────────────────────────────────────
#  Adaptive Retry Delay Helper
# ────────────────────────────────────────────────
def get_backoff_delay(attempt: int) -> float:
    """
    Compute an adaptive retry delay with exponential backoff.
    Capped by CONFIG.max_backoff multiplier.
    """
    return CONFIG.retry_delay * min(CONFIG.max_backoff, attempt)

# ────────────────────────────────────────────────
#  Example (for testing)
# ────────────────────────────────────────────────
if __name__ == "__main__":
    log = init_bridge_logger("PhotonBridgeTest")
    log.info(f"Bridge Config -> {CONFIG}")
    for i in range(1, 8):
        log.info(f"Retry {i} -> delay={get_backoff_delay(i):.1f}s")