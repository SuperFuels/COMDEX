# backend/modules/sqi/glyphnet_sync_layer.py

import json
import uuid
from datetime import datetime
from typing import Dict, Any

from backend.modules.gip.gip_packet import create_gip_packet
from backend.modules.gip.gip_adapter_http import transmit_packet

class GlyphNetSyncLayer:
    def __init__(self):
        self.synced_events = []

    def transmit_qglyph_state(self, qglyph_payload: Dict[str, Any], channel: str = "qglyph-sync") -> Dict:
        """
        Encodes and transmits a symbolic Q-Glyph state over GlyphNet via GIP.
        """
        packet = create_gip_packet(
            type="SQI-QGlyph",
            id=str(uuid.uuid4()),
            timestamp=str(datetime.utcnow()),
            channel=channel,
            payload=qglyph_payload
        )
        transmit_packet(packet)
        self.synced_events.append(packet)
        return packet

    def transmit_collapse_event(self, collapse_log: Dict[str, Any], channel: str = "collapse-log") -> Dict:
        """
        Broadcasts the result of a Q-Glyph collapse over GlyphNet.
        """
        packet = create_gip_packet(
            type="SQI-Collapse",
            id=str(uuid.uuid4()),
            timestamp=str(datetime.utcnow()),
            channel=channel,
            payload=collapse_log
        )
        transmit_packet(packet)
        self.synced_events.append(packet)
        return packet

    def get_synced_events(self) -> list:
        return self.synced_events