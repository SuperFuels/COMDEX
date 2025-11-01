# ──────────────────────────────────────────────
#  Tessaris SQI Resonance Bridge
#  Stage 14 - WaveScope + Hardware Pulse Relay
# ──────────────────────────────────────────────

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("SQIResonanceBridge")

# ──────────────────────────────────────────────
#  SQI Event Bus (safe import with guaranteed callable)
# ──────────────────────────────────────────────
def _safe_sqi_publish(packet: Dict[str, Any]):
    logger.debug(f"[WaveScope] (sim) fallback publish -> {packet.get('type', '?')}")

try:
    from backend.modules.sqi.sqi_event_bus import publish as sqi_publish
    if not callable(sqi_publish):
        sqi_publish = _safe_sqi_publish
except Exception as e:
    logger.warning(f"[WaveScope] SQI publish not available yet (lazy init): {e}")
    sqi_publish = _safe_sqi_publish

# Inside WaveScope.emit()
try:
    from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
    ucs = get_ucs_runtime()
    if hasattr(ucs, "visualizer") and ucs.visualizer:
        ucs.visualizer.update_resonance(
            container="symatics_resonance_coupling",
            resonance_index=R,
            phase_diff=Δφ,
        )
except Exception as e:
    logger.warning(f"[WaveScope] GHXVisualizer update failed: {e}")

# ──────────────────────────────────────────────
#  Safe Import: SQI Event Bus
# ──────────────────────────────────────────────
try:
    from backend.modules.sqi.sqi_event_bus import publish as sqi_publish
except Exception as e:
    logger.warning(f"[WaveScope] SQI publish not available yet (lazy init): {e}")

    def sqi_publish(packet: dict):
        logger.debug(f"[WaveScope] (sim) SQI publish placeholder -> {packet.get('type', '?')}")


# ──────────────────────────────────────────────
#  WaveScope Class Definition
# ──────────────────────────────────────────────
class WaveScope:
    """
    🌊 WaveScope - Simulated or hardware-bound coherence bus.
    Routes resonance metrics into GPIO or virtual analog channels.
    """

    def __init__(self, simulated: bool = True):
        self.simulated = simulated
        self.last_state: Optional[Dict[str, Any]] = None
        self.active = True

        if self.simulated:
            logger.info("🌊 WaveScope initialized in simulated mode.")
        else:
            try:
                import RPi.GPIO as GPIO  # type: ignore
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(18, GPIO.OUT)
                self.gpio = GPIO
                logger.info("🪩 WaveScope initialized on GPIO 18.")
            except Exception as e:
                logger.warning(f"[WaveScope] Hardware init failed -> fallback sim: {e}")
                self.simulated = True

    # ──────────────────────────────────────────────
    #  Emit resonance
    # ──────────────────────────────────────────────
    def emit(self, resonance: Dict[str, Any]) -> None:
        """Forward Φ-ψ resonance data to SQI bus and hardware/sim layer."""
        if not self.active:
            return

        self.last_state = resonance
        R = float(resonance.get("resonance_index", 0.0))
        Δφ = float(resonance.get("phase_diff", 0.0))

        packet = {
            "type": "sqi.resonance_update",
            "timestamp": time.time(),
            "payload": resonance,
        }
        try:
            sqi_publish(packet)
            logger.debug("[WaveScope] SQI publish -> resonance_update")
        except Exception as e:
            logger.warning(f"[WaveScope] SQI publish failed: {e}")

        # Hardware / simulated feedback
        try:
            if self.simulated:
                logger.debug(f"[WaveScope-Sim] R={R:.4f}, Δφ={Δφ:.4f}")
            else:
                duty = int(min(max(R, 0.0), 1.0) * 100)
                pwm = self.gpio.PWM(18, 1000)
                pwm.start(duty)
                time.sleep(0.05)
                pwm.stop()
        except Exception as e:
            logger.warning(f"[WaveScope] emit error: {e}")

    # ──────────────────────────────────────────────
    #  Stop bridge
    # ──────────────────────────────────────────────
    def stop(self):
        self.active = False
        if not self.simulated and hasattr(self, "gpio"):
            try:
                self.gpio.cleanup()
            except Exception:
                pass
        logger.info("WaveScope stopped.")


# ──────────────────────────────────────────────
#  Global Instance + Safe Accessor
# ──────────────────────────────────────────────
_wave_scope_instance: Optional[WaveScope] = None


def get_wave_scope() -> WaveScope:
    """Get or initialize the global WaveScope instance."""
    global _wave_scope_instance
    if _wave_scope_instance is None:
        try:
            _wave_scope_instance = WaveScope(simulated=True)
        except Exception as e:
            logger.warning(f"[WaveScope] init failed: {e}")
            _wave_scope_instance = WaveScope(simulated=True)
    return _wave_scope_instance


# ──────────────────────────────────────────────
#  Bridge entrypoint for CFA lazy import
# ──────────────────────────────────────────────
def emit_resonance(payload: Dict[str, Any]):
    """Emit a resonance update through the active WaveScope instance."""
    global wave_scope
    if wave_scope is None:
        logger.warning("[WaveScope] emit_resonance() called but no active instance.")
        return
    try:
        wave_scope.emit(payload)
    except Exception as e:
        logger.warning(f"[WaveScope] SQI publish failed: {e}")


# ──────────────────────────────────────────────
#  Singleton export
# ──────────────────────────────────────────────
wave_scope = WaveScope(simulated=True)