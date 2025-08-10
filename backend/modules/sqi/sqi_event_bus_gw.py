"""
Optional SQI bus mix-in to route through GlyphWave when enabled.
"""
from typing import Dict, Any
from backend.modules.glyphwave.adapters import send_packet, recv_packet
from backend.modules.glyphwave.feature_flag import gw_enabled

def sqi_publish(packet: Dict[str, Any]) -> None:
    """
    Wraps/forwards packets via GlyphWave if enabled, else fall back to existing bus.
    """
    if gw_enabled():
        send_packet(packet)
    else:
        # TODO: call your existing sqi_event_bus.publish(packet)
        pass

def sqi_poll() -> None:
    if not gw_enabled():
        return
    while True:
        p = recv_packet()
        if not p:
            break
        # TODO: hand back to existing bus consumer callback
        # e.g., sqi_event_bus.on_packet(p)