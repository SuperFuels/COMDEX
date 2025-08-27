import asyncio
import json
from typing import Dict, Optional

from backend.modules.ghx.ghx_websocket_server import broadcast_ghx_event
from backend.modules.symbolic.hst.symbolic_tree_types import SymbolicMeaningTree


def stream_hst_to_websocket(container_id: str, tree: SymbolicMeaningTree, context: Optional[str] = None):
    """
    Broadcast the SymbolicMeaningTree nodes/edges to GHX/QFC overlay clients via WebSocket.
    """
    try:
        payload = {
            "type": "hst_overlay",
            "container_id": container_id,
            "nodes": [n.to_dict() for n in tree.node_index.values()],
            "edges": [
                {"from": edge.source, "to": edge.target, "type": edge.type}
                for edge in tree.edges
            ],
            "context": context or "runtime"
        }
        asyncio.create_task(broadcast_ghx_event("hst_overlay", payload))
        print(f"📡 HST overlay broadcasted for {container_id} with {len(tree.node_index)} nodes")
    except Exception as e:
        print(f"❌ Failed to stream HST overlay: {e}")