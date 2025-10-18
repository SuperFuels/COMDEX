"""
🌊 WaveScope — Simulated Resonance Field Monitor
───────────────────────────────────────────────
Provides a simplified simulated layer for Φ–ψ resonance coupling
visualization and SQI bus emission.

Used when hardware WaveScope or SQI bus is unavailable.
"""

import logging
import random
from typing import Dict, Any

logger = logging.getLogger("WaveScope")

class WaveScope:
    def __init__(self, simulated: bool = True):
        self.simulated = simulated
        if self.simulated:
            logger.info("🌊 WaveScope initialized in simulated mode.")
        else:
            logger.info("🌊 WaveScope initialized (hardware mode).")

    # ────────────────────────────────────────────────
    #  Emit Resonance Event
    # ────────────────────────────────────────────────
    def emit(self, payload: Dict[str, Any]) -> None:
        """
        Process and broadcast Φ–ψ resonance data to the SQI layer.
        """
        try:
            R = float(payload.get("resonance_index", 0.0))
            phase_diff = float(payload.get("phase_diff", 0.0))
            logger.info(f"[WaveScope-Sim] R={R:.4f}, Δφ={phase_diff:.4f}")

            # In simulated mode, just log to the SQI channel
            try:
                from backend.modules.sqi.sqi_event_bus import publish as sqi_publish
                sqi_publish({
                    "type": "resonance_update",
                    "payload": payload,
                    "simulated": self.simulated,
                })
                logger.info("[WaveScope] SQI publish → resonance_update")
            except Exception as e:
                logger.warning(f"[WaveScope] SQI publish failed: {e}")

        except Exception as e:
            logger.error(f"[WaveScope] emit() failed: {e}", exc_info=True)