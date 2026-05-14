# File: backend/routes/ghost_routes.py

from fastapi import APIRouter
from backend.modules.DreamOS.ghost_entry import inject_ghost_from_gwv
from backend.modules.DreamOS.ghost_memory_writer import inject_ghost_memory
from backend.modules.websocket_manager import broadcast_event

router = APIRouter()

@router.post("/ghost/spawn")
async def spawn_ghost(container_id: str, gwv_trace: str):
    """
    Spawn a ghost trace: inject, store in memory, and broadcast.
    """
    ghost_path = inject_ghost_from_gwv(gwv_trace, container_id)
    scroll_id = inject_ghost_memory(container_id, gwv_trace)

    await broadcast_event("ghost_spawn", {
        "event_type": "ghost_spawn",
        "container_id": container_id,
        "ghost_trace_id": scroll_id,
    })

    return {"status": "ok", "ghost_path": ghost_path, "scroll_id": scroll_id}