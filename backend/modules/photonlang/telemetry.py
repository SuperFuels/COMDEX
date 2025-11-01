# ============================================================
# photonlang/telemetry.py - SQI event hook (v0.3)
# ============================================================

from __future__ import annotations
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def emit_sqi_event(event: str, payload: Dict[str, Any]) -> bool:
    """
    Unified SQI telemetry emitter (non-blocking, fault tolerant).
    Order:
      1) Push to SQI engine (if available)
      2) Local log for dev visibility
      3) Optional WS broadcast (if available)
    Returns True if any sink succeeded; otherwise False.
    """
    ts = time.time()
    packet = {
        "event": event,
        "timestamp": ts,
        "payload": payload,
    }

    ok = False

    # 1) SQI engine hook (new)
    try:
        from backend.modules.sqi.sqi_engine import push_sqi
        # include timestamp in payload for downstream
        push_sqi(event, {**payload, "timestamp": ts})
        ok = True
    except Exception:
        pass

    # 2) Local dev log
    try:
        logger.info("[SQI] %s %s", event, payload)
        ok = True or ok
    except Exception:
        pass

    # 3) Optional live WS bus hook
    try:
        from backend.modules.qfield.qfc_ws_broadcast import broadcast_telemetry
        broadcast_telemetry(packet)
        ok = True or ok
    except Exception:
        # Ignore missing/failed broadcast module
        pass

    if not ok:
        # last-ditch never-crash tracer
        try:
            print(f"[SQI-FAILSAFE] {event}: {payload}")
        except Exception:
            pass

    return ok

# backend/modules/photonlang/telemetry.py
def emit_page_event(event: str, payload: dict):
    """
    High-level Photon Page event hook (distinct from raw SQI points).
    """
    packet = {"event": f"page:{event}", "payload": payload}
    try:
        # fan out via SQI path
        emit_sqi_event(f"page:{event}", payload)
        # optional direct SQI engine hook (if present)
        try:
            from backend.modules.sqi.sqi_engine import push_sqi
            push_sqi(f"page:{event}", payload)
        except Exception:
            pass
        return True
    except Exception:
        return False

def emit_page_event(action: str, payload: dict):
    # piggybacks on SQI emitter
    return emit_sqi_event(f"photon_page_{action}", payload)