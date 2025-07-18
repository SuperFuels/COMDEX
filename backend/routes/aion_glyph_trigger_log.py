from fastapi import APIRouter
from backend.modules.memory.memory_engine import MemoryEngine

router = APIRouter()

@router.get("/api/aion/glyph-triggers/recent")
def get_recent_glyph_triggers(container: str = "default"):
    memory = MemoryEngine(container_id=container)
    entries = memory.search(role="trigger_log", limit=50)
    triggers = []
    for entry in entries:
        try:
            if entry.get("content", "").startswith("🧠 Glyph"):
                parts = entry["content"].split("'", 2)
                glyph = parts[1] if len(parts) > 1 else "?"
                reason = entry["content"].split("Reason:")[-1].strip()
                triggers.append({
                    "glyph": glyph,
                    "reason": reason,
                    "coord": entry.get("coord", ""),
                    "timestamp": entry.get("timestamp", "")
                })
        except Exception as e:
            continue
    return {"triggers": triggers}
