# ============================================================
# photonlang/telemetry.py — SQI event hook (v0.2)
# ============================================================

from __future__ import annotations
import time
import logging

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def emit_sqi_event(event: str, payload: dict):
    """
    Unified SQI telemetry emitter (non-blocking, fault tolerant).
    Called from photon executor and parallel capsule engine.
    """

    try:
        # Attach timestamp + event name
        packet = {
            "event": event,
            "timestamp": time.time(),
            "payload": payload,
        }

        # 🔹 Local dev: direct log
        logger.info(f"[SQI] {event} {payload}")

        # 🔹 Optional live WS bus hook
        try:
            from backend.modules.qfield.qfc_ws_broadcast import broadcast_telemetry
            broadcast_telemetry(packet)
        except Exception:
            # Ignore missing/failed broadcast module
            pass

        return True

    except Exception:
        # last-ditch never-crash tracer
        try:
            print(f"[SQI-FAILSAFE] {event}: {payload}")
        except Exception:
            pass
        return False