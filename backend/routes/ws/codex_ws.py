# 📁 routes/ws/codex_ws.py

from fastapi import APIRouter, WebSocket
from backend.modules.websocket_manager import websocket_manager
from backend.modules.codex.codex_core import CodexCore

router = APIRouter()
codex = CodexCore()

@router.websocket("/ws/codex")
async def codex_ws_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "glyph" in data:
                glyph = data["glyph"]
                context = data.get("context", {})
                result = codex.execute(glyph, context)

                await websocket_manager.broadcast({
                    "event": "glyph_execution",
                    "glyph": glyph,
                    "result": result,
                    "context": context
                })
    except Exception as e:
        print(f"[⚠️] WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)