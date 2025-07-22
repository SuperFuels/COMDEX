# File: backend/modules/gip/gip_packet.py

import uuid
import time
from datetime import datetime

def create_gip_packet(type: str, channel: str, payload: dict) -> dict:
    """
    Create a standardized GIP packet.

    Args:
        type (str): The packet type, e.g., 'glyph', 'teleport', 'memory'.
        channel (str): Logical routing channel (e.g., 'luxnet', 'glyphnet').
        payload (dict): The actual symbolic payload.

    Returns:
        dict: GIP packet with metadata.
    """
    return {
        "type": type,
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "channel": channel,
        "payload": payload,
    }

# Example usage:
# packet = create_gip_packet("glyph", "luxnet", {"symbol": "↔", "data": {...}})