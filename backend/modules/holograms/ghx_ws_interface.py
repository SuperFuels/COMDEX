import json
from fastapi import WebSocket, WebSocketDisconnect
from backend.modules.websocket_manager import manager
from backend.modules.hologram.holographic_renderer import HolographicRenderer
from backend.modules.hologram.ghx_encoder import encode_glyphs_to_ghx
from backend.modules.state.state_manager import load_container_by_id

class GHXWebSocketHandler:
    def __init__(self):
        self.active_sessions = {}

    async def connect(self, websocket: WebSocket, container_id: str):
        await websocket.accept()
        self.active_sessions[websocket] = container_id
        manager.add(websocket)
        await self.send_initial_projection(websocket, container_id)

    async def send_initial_projection(self, websocket: WebSocket, container_id: str):
        try:
            container = load_container_by_id(container_id)
            ghx_packet = encode_glyphs_to_ghx(container)
            renderer = HolographicRenderer(ghx_packet)
            renderer.render_glyph_field()
            projection = renderer.export_projection()

            await websocket.send_text(json.dumps({
                "event": "ghx_projection",
                "container_id": container_id,
                "payload": projection
            }))
        except Exception as e:
            await websocket.send_text(json.dumps({
                "event": "ghx_error",
                "error": str(e)
            }))

    async def receive(self, websocket: WebSocket, data: str):
        try:
            msg = json.loads(data)
            if msg.get("event") == "trigger_glyph":
                glyph_id = msg.get("glyph_id")
                container_id = self.active_sessions.get(websocket)
                container = load_container_by_id(container_id)
                ghx_packet = encode_glyphs_to_ghx(container)
                renderer = HolographicRenderer(ghx_packet)
                renderer.render_glyph_field()
                triggered = renderer.trigger_projection(glyph_id)

                if triggered:
                    await manager.broadcast(json.dumps({
                        "event": "glyph_triggered",
                        "glyph_id": glyph_id,
                        "activation": triggered
                    }))
        except Exception as e:
            await websocket.send_text(json.dumps({
                "event": "ghx_error",
                "error": str(e)
            }))

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_sessions:
            del self.active_sessions[websocket]
        manager.remove(websocket)


ghx_ws_handler = GHXWebSocketHandler()