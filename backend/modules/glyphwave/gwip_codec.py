"""
🌀 GWIP (GlyphWave IP) Codec
Encodes and decodes GlyphWave Information Packets (GWIP) from/to GIP.

This is a lossless wrapper that adds symbolic phase metadata
(frequency, phase, coherence) to standard GIP packets.
"""

from typing import Dict, Any
from time import time

from .constants import DEFAULT_FREQ_HZ, DEFAULT_PHASE_RAD, DEFAULT_COHERENCE


class GWIPCodec:
    """
    🔄 Minimal, lossless codec from GIP → GWIP and back.
    Adds modulation metadata and preserves original content under 'payload'.
    """

    schema_version = 1

    def encode(self, gip: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap a GIP packet with GWIP envelope and metadata.

        Args:
            gip (Dict[str, Any]): Standard GIP packet.

        Returns:
            Dict[str, Any]: GWIP-encoded packet.
        """
        return {
            "type": "gwip",
            "schema": self.schema_version,
            "created_at": time(),
            "envelope": {
                "freq": gip.get("freq", DEFAULT_FREQ_HZ),
                "phase": gip.get("phase", DEFAULT_PHASE_RAD),
                "coherence": gip.get("coherence", DEFAULT_COHERENCE),
                "tags": gip.get("tags", []),
            },
            "payload": gip,  # Full original packet retained
        }

    def decode(self, gwip: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unwrap a GWIP packet to recover original GIP payload.

        Args:
            gwip (Dict[str, Any]): A GWIP packet.

        Returns:
            Dict[str, Any]: Original GIP dictionary.
        """
        if gwip.get("type") != "gwip":
            return gwip  # fallback for plain GIP
        return dict(gwip.get("payload", {}))

    def upgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure a packet is GWIP-encoded.

        Args:
            packet (Dict[str, Any]): GIP or GWIP.

        Returns:
            Dict[str, Any]: Valid GWIP packet.
        """
        return self.encode(packet) if packet.get("type") != "gwip" else packet

    def downgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract raw GIP from a GWIP packet.

        Args:
            packet (Dict[str, Any]): GWIP or GIP.

        Returns:
            Dict[str, Any]: GIP-formatted packet.
        """
        return self.decode(packet)