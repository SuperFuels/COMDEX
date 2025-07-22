from fastapi import APIRouter, Query
from backend.modules.hexcore.memory_engine import MemoryEngine
from typing import List, Dict
from datetime import datetime

router = APIRouter()

@router.get("/api/aion/glyph-triggers/recent")
def get_recent_glyph_triggers(
    container: str = Query("default", description="Container ID to query triggers from"),
    limit: int = Query(50, description="Maximum number of recent trigger logs to return")
) -> Dict[str, List[Dict]]:
    memory = MemoryEngine(container_id=container)
    entries = memory.search(role="trigger_log", limit=limit)
    triggers = []

    for entry in entries:
        try:
            content = entry.get("content", "")
            if not content.startswith("🧠 Glyph"):
                continue

            # Extract glyph and reason
            glyph = "?"
            reason = "Unknown"
            if "'" in content:
                parts = content.split("'")
                glyph = parts[1] if len(parts) > 1 else "?"

            if "Reason:" in content:
                reason = content.split("Reason:")[-1].strip()

            triggers.append({
                "glyph": glyph,
                "reason": reason,
                "coord": entry.get("coord", "?"),
                "timestamp": entry.get("timestamp", ""),
            })
        except Exception:
            continue

    # Sort by most recent if timestamps are present
    def parse_ts(ts):
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.min

    triggers.sort(key=lambda e: parse_ts(e["timestamp"]), reverse=True)

    return {"container": container, "count": len(triggers), "triggers": triggers}