# backend/modules/glyphnet/glyphnet_transceiver.py

import logging
from typing import Optional, Callable, Dict, Any

from backend.modules.glyphnet.gip_adapter_wave import (
    encode_gip_to_waveform,
    decode_waveform_to_gip,
)
from backend.modules.glyphwave.feature_flag import gw_enabled

logger = logging.getLogger(__name__)

class GlyphNetTransceiver:
    """
    Handles encoding/decoding of GIP packets to waveform bytes,
    and routing them through the configured transport.
    """

    def __init__(self, transport=None):
        self.transport = transport
        self.enabled = gw_enabled()
        self.on_packet_received: Optional[Callable[[Dict[str, Any]], None]] = None

        if self.transport and hasattr(self.transport, "set_on_receive"):
            self.transport.set_on_receive(self.receive_packet)
            logger.debug("[GlyphNet] 🔌 Transport receive handler attached.")

    def send_packet(self, gip_packet: Dict[str, Any]) -> Optional[bytes]:
        """
        Sends a GIP packet as a waveform. If transport exists, it is used.
        """
        if not self.enabled:
            logger.debug("[GlyphNet] 🔇 GWave disabled, skipping send.")
            return None

        try:
            waveform = encode_gip_to_waveform(gip_packet)
            if self.transport:
                self.transport.send(waveform)
                logger.info("[GlyphNet] 📤 GIP packet sent via transport.")
            else:
                logger.warning("[GlyphNet] ⚠️ No transport set; waveform not sent.")
            return waveform
        except Exception as e:
            logger.exception(f"[GlyphNet] ❌ Failed to send packet: {e}")
            return None

    def receive_packet(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Receives waveform bytes and decodes them into a GIP packet.
        Triggers optional callback on successful decode.
        """
        if not self.enabled:
            logger.debug("[GlyphNet] 🔇 GWave disabled, skipping receive.")
            return None

        try:
            gip_packet = decode_waveform_to_gip(data)
            logger.info("[GlyphNet] 📥 GIP packet received.")
            if self.on_packet_received:
                self.on_packet_received(gip_packet)
            return gip_packet
        except Exception as e:
            logger.exception(f"[GlyphNet] ❌ Failed to decode packet: {e}")
            return None

    def set_transport(self, transport):
        """
        Dynamically assigns the transport layer.
        """
        self.transport = transport
        if hasattr(self.transport, "set_on_receive"):
            self.transport.set_on_receive(self.receive_packet)
            logger.debug("[GlyphNet] 🔌 Transport receive handler attached (dynamic).")

    def set_on_packet_received(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Sets a callback for handling successfully received GIP packets.
        """
        self.on_packet_received = callback

# ════════════════════════════════════════════════════════════════
# 🔁 Singleton Wrapper for Global Packet Transmission
# ════════════════════════════════════════════════════════════════

_transceiver_instance = GlyphNetTransceiver()

def transmit_gwave_packet(packet: Dict[str, Any]) -> Optional[bytes]:
    """
    Global helper to transmit a GIP packet via the default GlyphNet transceiver.
    Used in runtime modules to avoid direct transceiver instantiation.
    """
    return _transceiver_instance.send_packet(packet)