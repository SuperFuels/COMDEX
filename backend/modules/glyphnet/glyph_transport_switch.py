# File: backend/modules/glyphnet/glyph_transport_switch.py

import logging
from typing import Dict, Any, Optional

from backend.modules.glyphnet.glyph_beacon import emit_beacon
from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform, save_wavefile
from backend.modules.glyphnet.glyphnet_packet import create_gip_packet
from backend.modules.glyphnet.glyphwave_simulator import (
    simulate_waveform_loopback,
    simulate_waveform_transmission,
)
from backend.modules.glyphnet.broadcast_utils import broadcast_ws_event  # ✅ WebSocket broadcast
from backend.modules.glyphnet.glyphnet_transceiver import transmit_gwave_packet  # ✅ GWave integration
from backend.modules.glyphnet.qkd_policy import enforce_qkd_policy, QKDPolicyError  # ✅ QKD policy
from backend.modules.qkd.qkey_model import GKey  # shared QKD session key model

logger = logging.getLogger(__name__)

# Supported transport types
TRANSPORT_CHANNELS = {"tcp", "beacon", "radio", "light", "local", "gwave"}

# Preferred order for auto-selection
FALLBACK_ORDER = ["gwave", "tcp", "beacon", "radio", "light", "local"]


# ───────────────────────────────────────────────
# Glyph Packet Routing
# ───────────────────────────────────────────────
def route_glyph_packet(
    glyphs: Any,
    transport: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Wrapper to route glyphs directly (constructs a .gip packet internally).
    """
    packet = create_gip_packet(
        payload={"glyphs": glyphs},
        sender=(metadata or {}).get("sender", "system"),
        metadata=metadata,
    )
    success = route_gip_packet(packet, transport, options)
    return {
        "status": "ok" if success else "failed",
        "transport": transport or "auto",
        "packet": packet,
    }


def route_gip_packet(
    packet: Dict[str, Any],
    transport: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Routes a .gip packet through the specified transport mechanism.
    If no transport is specified, tries auto-select in FALLBACK_ORDER.
    """
    try:
        if transport:
            chosen = transport.lower()
            if chosen not in TRANSPORT_CHANNELS:
                logger.warning(f"[Transport] Unsupported channel: {chosen}")
                return False
            return _dispatch_packet(packet, chosen, options)

        # Auto-select: try channels in order until one succeeds
        for channel in FALLBACK_ORDER:
            if _dispatch_packet(packet, channel, options):
                logger.info(f"[Transport] Auto-selected channel: {channel}")
                return True

        logger.error("[Transport] All transport channels failed")
        return False

    except Exception as e:
        logger.exception(f"[Transport] Failed to route packet via {transport or 'auto'}: {e}")
        return False


# ───────────────────────────────────────────────
# Internal Dispatcher with QKD enforcement
# ───────────────────────────────────────────────
def _dispatch_packet(
    packet: Dict[str, Any],
    transport: str,
    options: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Internal helper to actually perform the transmission.
    Applies QKD policy enforcement before sending.
    """
    try:
        # ── QKD Gate ──
        gkey: Optional[GKey] = (options or {}).get("gkey")
        try:
            enforce_qkd_policy(packet, gkey)
        except QKDPolicyError as qkd_err:
            logger.error(f"[Transport] QKD enforcement failed: {qkd_err}")
            return False

        payload = packet.get("payload", {})
        glyphs = payload.get("glyphs", [])

        if transport == "tcp":
            broadcast_ws_event("glyph_packet", packet)
            logger.info("[Transport] Routed via TCP/GlyphNet WS")

        elif transport == "gwave":
            transmit_gwave_packet(packet)
            logger.info("[Transport] Routed via GWave Transceiver")

        elif transport == "beacon":
            emit_beacon(
                glyphs,
                sender=packet.get("sender"),
                destination=packet.get("target"),
            )
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
            try:
                result = simulate_waveform_transmission(glyphs, sender=packet.get("sender", "local"))
                logger.info(
                    f"[Transport] Routed via Local Simulator (file={result['trace']['file']})"
                )
            except Exception as sim_err:
                logger.warning(f"[Transport] Local simulator failed, falling back: {sim_err}")
                simulate_waveform_loopback(glyphs)
            logger.info("[Transport] Routed via Local Loopback")

        else:
            logger.warning(f"[Transport] Unsupported channel: {transport}")
            return False

        return True

    except Exception as e:
        logger.error(f"[Transport] Dispatch failed on channel {transport}: {e}")
        return False