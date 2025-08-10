"""
GWIP (GlyphWave IP) lossless wrapper for GIP.
"""
from typing import Dict, Any
from time import time
from .constants import DEFAULT_FREQ_HZ, DEFAULT_PHASE_RAD, DEFAULT_COHERENCE

class GWIPCodec:
    """
    Minimal, lossless encode/decode of GIP→GWIP with phase/coherence envelope.
    """
    schema_version = 1

    def encode(self, gip: Dict[str, Any]) -> Dict[str, Any]:
        # keep original packet fully intact under "payload"
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
            "payload": gip,  # lossless
        }

    def decode(self, gwip: Dict[str, Any]) -> Dict[str, Any]:
        # graceful degrade if already plain gip
        if gwip.get("type") != "gwip":
            return gwip
        return dict(gwip.get("payload", {}))

    # Back-compat helpers used by routers
    def upgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        return self.encode(packet) if packet.get("type") != "gwip" else packet

    def downgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        return self.decode(packet)