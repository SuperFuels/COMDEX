"""
📬 GlyphWave SQI Adapter
Optional SQI bus mix-in to route events through GlyphWave when enabled.

🔧 Features:
- Wraps sqi_event_bus.publish with GW feature gating
- Emits telemetry to wave_scope (metrics tracking)
- Broadcasts to HUD overlays and GHXVisualizer (via WebSocket)
- Routes events through GlyphWave carrier if enabled
"""

from typing import Dict, Any, Callable, Optional
from backend.modules.glyphwave.feature_flag import gw_enabled
from backend.modules.glyphwave.wavescope import WaveScope
from backend.modules.glyphwave.telemetry_handler import log_beam, get_wave_scope
from backend.modules.glyphwave.adapters.glyphnet_adapter import send_packet, recv_packet
# 🔁 Fallback publish function (e.g. sqi_event_bus.publish)
_fallback_publish: Optional[Callable[[Dict[str, Any]], None]] = None


def init_gw_publish_wrapper(fallback_publish_func: Callable[[Dict[str, Any]], None]) -> None:
    """
    Initializes the GlyphWave SQI wrapper with the original sqi_event_bus.publish function.
    This MUST be called once during system bootstrap.
    
    Args:
        fallback_publish_func: The original publish() function from sqi_event_bus
    """
    global _fallback_publish
    _fallback_publish = fallback_publish_func


def publish(event: Dict[str, Any]) -> None:
    """
    Main SQI publish entrypoint.
    
    ✅ Always logs to WaveScope
    ✅ Streams to HUD overlays via WebSocket
    ✅ Sends via GlyphWave if enabled
    ✅ Falls back to original sqi_event_bus.publish() if disabled
    
    Args:
        event: Dictionary containing event details (type, meta, etc.)
    """
    event_type = event.get("type", "unknown")
    meta = event.get("meta", {})

    # Local instrumentation
    wave_scope.log_beam_event(event_type, meta=meta)
    maybe_stream_to_websocket(event)  # GHXVisualizer + CodexHUD
    stream_to_hud(event)              # Other frontend HUDs

    if gw_enabled():
        send_packet(event)
    elif _fallback_publish:
        _fallback_publish(event)
    else:
        raise RuntimeError("🛑 GW fallback publish not initialized. Call init_gw_publish_wrapper().")


def poll() -> None:
    """
    Continuously polls for incoming packets from GlyphWave and routes them
    to the fallback SQI event bus.

    Intended for runtime thread or loop.

    Raises:
        Warning if fallback is missing
    """
    if not gw_enabled():
        return

    while True:
        packet = recv_packet()
        if not packet:
            break

        if _fallback_publish:
            _fallback_publish(packet)
        else:
            print("⚠️ [GlyphWave] Received packet but no fallback publish function is set.")