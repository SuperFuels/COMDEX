# backend/modules/glyphnet/glyph_transport_switch.py

import logging
from typing import Dict, Any, Optional

from backend.modules.glyphnet.glyph_beacon import emit_beacon_signal
from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform, save_wavefile
from backend.modules.glyphnet.glyphnet_packet import create_glyph_packet, push_symbolic_packet
from backend.modules.glyphnet.glyphwave_simulator import simulate_waveform_loopback

logger = logging.getLogger(__name__)

# Supported transport types
TRANSPORT_CHANNELS = {"beacon", "radio", "light", "tcp", "local"}


def route_glyph_packet(
    glyphs: Any,
    transport: str = "tcp",
    metadata: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Wrapper to route glyphs directly (constructs packet internally).
    """
    packet = create_glyph_packet(glyphs=glyphs, metadata=metadata or {})
    success = route_gip_packet(packet, transport, options)
    return {
        "status": "ok" if success else "failed",
        "transport": transport,
        "packet": packet
    }


def route_gip_packet(
    packet: Dict[str, Any],
    transport: str = "tcp",
    options: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Routes a .gip packet through the specified transport mechanism.
    """
    try:
        transport = transport.lower()
        if transport not in TRANSPORT_CHANNELS:
            logger.warning(f"[Transport] Unsupported channel: {transport}")
            return False

        payload = packet.get("payload", {})
        glyphs = payload.get("glyphs", [])

        if transport == "tcp":
            push_symbolic_packet(packet)
            logger.info("[Transport] Routed via TCP/GlyphNet")

        elif transport == "beacon":
            emit_beacon_signal(payload)
            logger.info("[Transport] Routed via Beacon Emitter")

        elif transport == "radio":
            waveform = glyphs_to_waveform(glyphs)
            save_wavefile("radio_signal.wav", waveform)
            logger.info("[Transport] Routed via Radio (waveform generated)")

        elif transport == "light":
            waveform = glyphs_to_waveform(glyphs)
            save_wavefile("light_signal.wav", waveform)
            logger.info("[Transport] Routed via Light (waveform generated)")

        elif transport == "local":
            simulate_waveform_loopback(glyphs)
            logger.info("[Transport] Routed via Local Loopback")

        return True

    except Exception as e:
        logger.exception(f"[Transport] Failed to route packet via {transport}: {e}")
        return False