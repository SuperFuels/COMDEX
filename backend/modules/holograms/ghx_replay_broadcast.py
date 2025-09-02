# File: backend/modules/holograms/ghx_replay_broadcast.py

import json
from backend.modules.network.websocket_server import broadcast_event
from backend.modules.symbolic.symbolic_tree_types import SymbolicMeaningTree

def stream_symbolic_tree_replay(tree: SymbolicMeaningTree, container_id: str = None):
    """
    Broadcast the replayPaths and overlays from a SymbolicMeaningTree to GHX/QFC clients.
    """
    if not tree or not tree.trace or not tree.trace.replayPaths:
        print("[GHX-Broadcast] ⚠️ No replay paths found in symbolic tree.")
        return

    payload = {
        "type": "symbolic_tree_replay",
        "container_id": container_id,
        "replayPaths": tree.trace.replayPaths,
        "entropyOverlay": tree.trace.entropyOverlay,
        "goalScores": {
            node_id: node.goal_score
            for node_id, node in tree.node_index.items()
            if node.goal_score is not None
        },
    }

    print(f"[GHX-Broadcast] 📡 Broadcasting symbolic replay for container {container_id or 'unknown'}")
    broadcast_event("ghx_replay", payload)