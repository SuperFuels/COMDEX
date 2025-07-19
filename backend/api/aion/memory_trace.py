# backend/api/aion/memory_trace.py

from fastapi import APIRouter, Query
from typing import List
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.state_manager import StateManager

router = APIRouter()

@router.get("/api/aion/memory-trace")
def get_memory_trace(container_id: str = Query(default=None)):
    """Fetch glyph trigger memory logs via MemoryBridge."""
    state = StateManager()
    cid = container_id or state.get_current_container_id() or "default"
    memory = MemoryEngine(cid)
    logs = memory.fetch(role="trigger_log", limit=100)

    parsed = []
    for entry in logs:
        parsed.append({
            "timestamp": entry.get("timestamp"),
            "content": entry.get("content"),
            "metadata": entry.get("metadata", {}),
        })

    return {"container_id": cid, "traces": parsed}