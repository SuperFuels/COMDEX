# backend/api/aion/get_memory_trace.py

from fastapi import APIRouter
from modules.consciousness.state_manager import StateManager
from modules.memory.memory_engine import MemoryEngine
from datetime import datetime

router = APIRouter()

@router.get("/api/aion/memory-trace")
async def get_memory_trace():
    state = StateManager()
    container_id = state.get_current_container_id() or "default"
    memory = MemoryEngine(container_id)

    logs = memory.search(role="trigger_log")
    traces = []

    for log in logs:
        try:
            content = log.get("content", "")
            glyph = content.split("'")[1] if "'" in content else "?"
            context_str = content.split("reason: ")[-1] if "reason:" in content else "{}"
            timestamp = log.get("timestamp") or datetime.utcnow().isoformat()
            trace = {
                "timestamp": timestamp,
                "glyph": glyph,
                "context": {"reason": context_str},
                "memory_links": memory.search_links(glyph),
            }
            traces.append(trace)
        except Exception:
            continue

    return {"traces": traces}