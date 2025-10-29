"""
🧩 SCI Memory Browser + Replay API
----------------------------------
Provides endpoints to:
 - List stored Resonant Memory scrolls (for the SCI IDE Memory sidebar)
 - Replay a selected scroll into QFC / SCI runtime visualization
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any

# ------------------------------------------------------------
# Imports from backend modules
# ------------------------------------------------------------
try:
    from backend.modules.resonant_memory.resonant_memory_loader import list_scrolls_from_memory, load_scroll_from_memory
except ImportError:
    def list_scrolls_from_memory(user_id: str, limit: int = 20):
        print("⚠️ Stub resonant memory listing.")
        return []

    def load_scroll_from_memory(user_id: str, scroll_id: str):
        print(f"⚠️ Stub resonant memory load: {scroll_id}")
        return {"id": scroll_id, "content": "stub content"}

try:
    from backend.modules.sci.qfc_ws_broadcaster import broadcast_qfc_state
except ImportError:
    async def broadcast_qfc_state(field_state: Dict[str, Any], **kwargs):
        print(f"[StubQFC] Would broadcast: {list(field_state.keys())}")

try:
    from backend.modules.sci.sci_replay_injector import SCIReplayInjector
except ImportError:
    class SCIReplayInjector:
        async def replay_scroll(self, scroll_data: Dict[str, Any]):
            print(f"[StubReplay] Replaying scroll: {scroll_data.get('id')}")
            return {"ok": True, "status": "stub"}

# ------------------------------------------------------------
# Router
# ------------------------------------------------------------
router = APIRouter(prefix="/api/sci", tags=["SCI Memory"])

# ------------------------------------------------------------
# GET /api/sci/memory_scrolls
# ------------------------------------------------------------
@router.get("/memory_scrolls", response_model=List[Dict[str, Any]])
async def list_memory_scrolls(user_id: str = Query(...), limit: int = Query(20)):
    """
    Returns a list of memory scrolls (latest first) for the given user.
    Used by the SCI IDE memory sidebar.
    """
    try:
        scrolls = list_scrolls_from_memory(user_id=user_id, limit=limit)
        return scrolls
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list memory scrolls: {e}")

# ------------------------------------------------------------
# POST /api/sci/replay_scroll
# ------------------------------------------------------------
@router.post("/replay_scroll")
async def replay_scroll(payload: Dict[str, Any]):
    """
    Replays a specific Resonant Memory scroll into the QFC visualization.
    Expects JSON: { "user_id": "...", "scroll_id": "..." }
    """
    user_id = payload.get("user_id")
    scroll_id = payload.get("scroll_id")

    if not user_id or not scroll_id:
        raise HTTPException(status_code=400, detail="user_id and scroll_id are required")

    try:
        # Load scroll data
        scroll_data = load_scroll_from_memory(user_id, scroll_id)
        if not scroll_data:
            raise HTTPException(status_code=404, detail=f"Scroll {scroll_id} not found")

        # Replay using SCI injector
        injector = SCIReplayInjector()
        result = await injector.replay_scroll(scroll_data)

        # Broadcast to QFC for live HUD update
        await broadcast_qfc_state(scroll_data.get("content", {}), observer_id="sci_memory_replay")

        return {"ok": True, "scroll_id": scroll_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {e}")