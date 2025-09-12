# ✅ File: backend/modules/visualization/broadcast_qfc_update.py

from typing import Dict, Any
from backend.modules.visualization.qfc_websocket_bridge import send_qfc_update

async def broadcast_qfc_update(container_id: str, payload: Dict[str, Any]) -> None:
    """
    Async helper to broadcast new QFC data (nodes, links) to the frontend.

    Args:
        container_id (str): ID of the symbolic container being updated
        payload (Dict[str, Any]): Must contain "nodes" and/or "links"
    """
    try:
        render_packet = {
            "source": f"container::{container_id}",
            "payload": {
                "nodes": payload.get("nodes", []),
                "links": payload.get("links", []),
            },
        }
        await send_qfc_update(render_packet)
        print(f"📡 QFC broadcast sent for: {container_id} | Nodes: {len(render_packet['payload']['nodes'])}")

    except Exception as e:
        print(f"❌ Failed to broadcast QFC update for {container_id}: {e}")