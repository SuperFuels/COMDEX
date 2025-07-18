# runtime_broadcast.py

from backend.modules.webhook_data.glyph_summary import get_glyph_summary
from backend.modules.dimensions.avatar_core import AIONAvatar
from backend.modules.websocket_manager import websocket_manager

avatar = AIONAvatar(container_id="default")  # Replace with dynamic container if needed

async def broadcast_runtime_updates():
    try:
        summary = get_glyph_summary()
        await websocket_manager.broadcast({
            "event": "glyph_summary",
            "data": summary,
        })

        runtime = {
            "tick": avatar.tick_count,
            "mode": avatar.mode,
            "position": avatar.position,
            "container": avatar.container_id,
            "active_glyphs": summary.get("total", 0),
        }

        await websocket_manager.broadcast({
            "event": "avatar_runtime",
            "data": runtime,
        })

    except Exception as e:
        print(f"[❌] Error in runtime broadcast: {e}")