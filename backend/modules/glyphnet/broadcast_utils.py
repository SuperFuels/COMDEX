# backend/modules/glyphnet/broadcast_utils.py

from typing import Dict, Any
from backend.modules.websocket_manager import websocket_manager  

def broadcast_ws_event(event_type: str, data: Dict[str, Any]) -> None:
    websocket_manager.broadcast({
        "type": event_type,
        "data": data
    })