# backend/modules/qfield/qfc_ws_broadcast.py

import asyncio
from typing import Dict, Optional, Any
from backend.modules.websocket_manager import send_ws_message as ws_server

def send_qfc_payload(payload: Dict[str, Any], mode: str = "live") -> None:
    """
    Broadcast a QFC payload using WebSocket.

    Args:
        payload (Dict): The symbolic payload (e.g., from build_qfc_view).
        mode (str): Broadcast mode, e.g., "live", "replay", "mutation"
    """
    try:
        payload["mode"] = mode
        asyncio.create_task(ws_server(payload, tag="qfc_payload"))
    except Exception as e:
        print(f"❌ QFC WebSocket broadcast failed: {e}")