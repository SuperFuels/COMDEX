# backend/modules/glyphnet/glyph_transport_config.py

from typing import Callable, Dict, Any
import logging

from backend.modules.glyphnet.glyph_beacon import emit_beacon
from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform
from backend.modules.glyphnet.glyphnet_packet import create_glyph_packet

logger = logging.getLogger(__name__)

# Transport handler signature
TransportHandler = Callable[[Dict[str, Any], Dict[str, Any]], bool]

# Registry of transport methods
TRANSPORT_REGISTRY: Dict[str, TransportHandler] = {}


def register_transport(name: str, handler: TransportHandler):
    TRANSPORT_REGISTRY[name] = handler
    logger.info(f"[TransportConfig] Registered transport: {name}")


def get_transport(name: str) -> TransportHandler:
    return TRANSPORT_REGISTRY.get(name)


# Default transport implementations
def radio_transport(packet: Dict[str, Any], options: Dict[str, Any]) -> bool:
    logger.info("[Transport] Sending packet via RADIO")
    try:
        waveform = glyphs_to_waveform(packet["glyphs"])
        # Stubbed: In real setup, send waveform to radio transmitter
        logger.debug(f"[Radio] Simulated waveform: {waveform[:10]}...")
        return True
    except Exception as e:
        logger.exception("[Radio] Failed to send via radio")
        return False


def beacon_transport(packet: Dict[str, Any], options: Dict[str, Any]) -> bool:
    logger.info("[Transport] Sending packet via BEACON")
    try:
        emit_beacon(packet)
        return True
    except Exception as e:
        logger.exception("[Beacon] Failed to emit")
        return False


def local_transport(packet: Dict[str, Any], options: Dict[str, Any]) -> bool:
    logger.info("[Transport] Processing packet locally")
    return True


# Pre-register common transports
register_transport("radio", radio_transport)
register_transport("beacon", beacon_transport)
register_transport("local", local_transport)