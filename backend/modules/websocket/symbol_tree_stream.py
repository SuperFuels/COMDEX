# File: backend/modules/websocket/symbol_tree_stream.py

import json
import gzip
import asyncio
from fastapi import WebSocket, APIRouter, WebSocketDisconnect
from backend.modules.symbolic.symbol_tree_generator import build_tree_from_container
from backend.modules.knowledge_graph.container_loader import load_container_by_id
from backend.modules.websocket.connection_manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/symbol_tree/{container_id}")
async def symbol_tree_stream(websocket: WebSocket, container_id: str):
    await manager.connect(websocket)
    try:
        # Step 1: Load container
        container = load_container_by_id(container_id)
        if not container:
            await websocket.send_json({"error": "Container not found."})
            return

        # Step 2: Build symbolic tree
        tree = build_tree_from_container(container)

        # Step 3: Serialize + compress
        data = json.dumps(tree.to_dict(), indent=2)
        compressed = gzip.compress(data.encode())

        # Step 4: Send tree payload
        await websocket.send_bytes(compressed)

        # Step 5: Optional: Push live updates (e.g. mutation, replay, etc)
        while True:
            # In a real system, hook into a mutation event queue
            await asyncio.sleep(5)
            # You could check for mutation diffs and push them here

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await websocket.send_json({"error": f"Internal error: {str(e)}"})
        manager.disconnect(websocket)