# backend/routes/aion_runtime_rewind.py

from fastapi import APIRouter, Query
from backend.modules.consciousness.state_manager import get_state_manager
from backend.modules.container_runtime import get_container_runtime

router = APIRouter()

@router.get("/api/aion/runtime/rewind")
def get_rewind_snapshot(tick: int = Query(..., description="Rewind tick index")):
    runtime = get_container_runtime()
    buffer = runtime.rewind_buffer

    if tick < 0 or tick >= len(buffer):
        return {"error": "Invalid tick index", "max": len(buffer) - 1}

    snapshot = buffer[tick]
    return {
        "tick": tick,
        "cubes": snapshot["cubes"]
    }