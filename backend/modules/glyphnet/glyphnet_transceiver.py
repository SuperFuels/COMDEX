# File: backend/modules/glyphnet/glyphnet_transceiver.py

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

    def __init__(self, transport: Optional[Any] = None):
        self.transport = transport
        self.enabled: bool = gw_enabled()
        self.on_packet_received: Optional[Callable[[Dict[str, Any]], None]] = None

        if self.transport:
            self._attach_transport(self.transport)

    # ──────────────────────────────────────────────
    # Sending
    # ──────────────────────────────────────────────
    def send_packet(self, gip_packet: Dict[str, Any]) -> Optional[bytes]:
        """
        Sends a GIP packet as a waveform. If a transport is available,
        it will be used to transmit the waveform.
        """
        if not self.enabled:
            logger.debug("[GlyphNet:TX] 🔇 Disabled, skipping send.")
            return None

        try:
            waveform = encode_gip_to_waveform(gip_packet)
            if self.transport and hasattr(self.transport, "send"):
                self.transport.send(waveform)
                logger.info("[GlyphNet:TX] 📤 Packet sent via transport.")
            else:
                logger.warning("[GlyphNet:TX] ⚠️ No transport or missing send(); waveform not sent.")
            return waveform
        except Exception as e:
            logger.exception(f"[GlyphNet:TX] ❌ Failed to send packet: {e}")
            return None

    # ──────────────────────────────────────────────
    # Receiving
    # ──────────────────────────────────────────────
    def receive_packet(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Receives waveform bytes and decodes them into a GIP packet.
        Triggers the optional callback if decoding succeeds.
        """
        if not self.enabled:
            logger.debug("[GlyphNet:RX] 🔇 Disabled, skipping receive.")
            return None

        try:
            gip_packet = decode_waveform_to_gip(data)
            logger.info("[GlyphNet:RX] 📥 Packet received.")
            if self.on_packet_received:
                try:
                    self.on_packet_received(gip_packet)
                except Exception as cb_err:
                    logger.warning(f"[GlyphNet:RX] ⚠️ on_packet_received callback failed: {cb_err}")
            return gip_packet
        except Exception as e:
            logger.exception(f"[GlyphNet:RX] ❌ Failed to decode packet: {e}")
            return None

    # ──────────────────────────────────────────────
    # Configuration
    # ──────────────────────────────────────────────
    def set_transport(self, transport: Any) -> None:
        """
        Dynamically assigns the transport layer.
        """
        self.transport = transport
        self._attach_transport(transport)
        logger.debug("[GlyphNet] 🔌 Transport layer dynamically set.")

    def _attach_transport(self, transport: Any) -> None:
        """
        Attach a receive handler to the transport if supported.
        """
        if hasattr(transport, "set_on_receive"):
            transport.set_on_receive(self.receive_packet)
            logger.debug("[GlyphNet] 🔌 Transport receive handler attached.")

    def set_on_packet_received(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Sets a callback for handling successfully received GIP packets.
        """
        self.on_packet_received = callback

    # ──────────────────────────────────────────────
    # Enable/Disable Controls
    # ──────────────────────────────────────────────
    def enable(self) -> None:
        """Enable the transceiver runtime."""
        self.enabled = True
        logger.info("[GlyphNet] ✅ Transceiver enabled.")

    def disable(self) -> None:
        """Disable the transceiver runtime (no send/receive)."""
        self.enabled = False
        logger.info("[GlyphNet] ⛔ Transceiver disabled.")

    def is_enabled(self) -> bool:
        """Return True if transceiver is active."""
        return self.enabled


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


def set_global_transport(transport: Any) -> None:
    """
    Dynamically configure the global transceiver transport.
    Useful for bootstrapping runtime transports (e.g., WebSocket, RF).
    """
    _transceiver_instance.set_transport(transport)


def set_global_receive_callback(callback: Callable[[Dict[str, Any]], None]) -> None:
    """
    Set a global callback for received GIP packets.
    """
    _transceiver_instance.set_on_packet_received(callback)


def enable_global_transceiver() -> None:
    """Enable the global GlyphNet transceiver."""
    _transceiver_instance.enable()


def disable_global_transceiver() -> None:
    """Disable the global GlyphNet transceiver."""
    _transceiver_instance.disable()


def is_global_transceiver_enabled() -> bool:
    """Check if the global GlyphNet transceiver is enabled."""
    return _transceiver_instance.is_enabled()