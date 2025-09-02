import asyncio
import json
from typing import Dict, List, Optional

from backend.modules.symbolic.symbolic_meaning_tree import SymbolicMeaningTree
from backend.modules.websocket_manager import broadcast_event


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
        asyncio.create_task(broadcast_event("hst_overlay", payload))
        print(f"📡 HST overlay broadcasted for {container_id} with {len(tree.node_index)} nodes")
    except Exception as e:
        print(f"❌ Failed to stream HST overlay: {e}")


def broadcast_replay_paths(container_id: str, replay_paths: List[Dict], context: Optional[str] = None):
    """
    Broadcast replay path overlays (mutation or prediction trails) to GHX/QFC visualizers.
    """
    try:
        payload = {
            "type": "replay_trails",
            "container_id": container_id,
            "replay_paths": replay_paths,
            "context": context or "prediction_engine"
        }
        asyncio.create_task(broadcast_event("replay_trails", payload))
        print(f"🛰️ Replay trails broadcasted for {container_id} ({len(replay_paths)} paths)")
    except Exception as e:
        print(f"❌ Failed to broadcast replay trails: {e}")