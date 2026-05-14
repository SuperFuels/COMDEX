# runtime_broadcast.py

from backend.modules.webhook_data.glyph_summary import get_glyph_summary
from backend.modules.dimensions.avatar_core import AIONAvatar
from backend.modules.websocket_manager import websocket_manager
import traceback

def get_avatar_runtime_data(avatar: AIONAvatar, summary: dict) -> dict:
    return {
        "tick": avatar.tick_count,
        "mode": avatar.mode,
        "position": avatar.position,
        "container": avatar.container_id,
        "active_glyphs": summary.get("total", 0),
    }

async def broadcast_runtime_updates(container_id: str = "default"):
    try:
        avatar = AIONAvatar(container_id=container_id)
        summary = get_glyph_summary()

        await websocket_manager.broadcast({
            "event": "glyph_summary",
            "data": summary,
        })

        runtime_data = get_avatar_runtime_data(avatar, summary)

        await websocket_manager.broadcast({
            "event": "avatar_runtime",
            "data": runtime_data,
        })

    except Exception as e:
        print(f"[❌] Error in runtime broadcast: {e}")
        traceback.print_exc()