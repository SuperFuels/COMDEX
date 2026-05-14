# backend/api/aion/memory_trace.py

from fastapi import APIRouter, Query
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.state_manager import StateManager

router = APIRouter()

@router.get("/aion/memory-trace")  # 🔧 No `/api` here
def get_memory_trace(container_id: str = Query(None)):
    """Fetch glyph trigger memory logs via MemoryBridge."""
    try:
        state = StateManager()
        cid = container_id or state.get_current_container_id() or "default"
        memory = MemoryEngine(cid)
        logs = memory.fetch(role="trigger_log", limit=100)

        parsed = [
            {
                "timestamp": entry.get("timestamp"),
                "content": entry.get("content"),
                "metadata": entry.get("metadata", {}),
            }
            for entry in logs
        ]

        return {"container_id": cid, "traces": parsed}

    except Exception as e:
        return {"error": str(e)}