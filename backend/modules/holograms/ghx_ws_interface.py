# File: backend/modules/hologram/ghx_ws_interface.py

import json
import logging
from fastapi import WebSocket, WebSocketDisconnect

from backend.modules.websocket_manager import manager
from backend.modules.hologram.holographic_renderer import HolographicRenderer
from backend.modules.hologram.ghx_encoder import encode_glyphs_to_ghx
from backend.modules.state.state_manager import load_container_by_id

# ✅ Optional: respect backend config flag for GHX logging
try:
    from backend.config import ENABLE_GLYPH_LOGGING
except Exception:
    ENABLE_GLYPH_LOGGING = True  # safe default

# ✅ Optional: safe GHX log shim — never raises even if interface changes
try:
    from backend.modules.hologram.ghx_logging import safe_ghx_log
except Exception:
    def safe_ghx_log(ghx, evt):
        # No-op fallback if helper isn't present
        try:
            logging.debug("[GHX][safe_ghx_log missing helper] %s", evt)
        except Exception:
            pass


class GHXWebSocketHandler:
    def __init__(self):
        self.active_sessions = {}

    async def connect(self, websocket: WebSocket, container_id: str):
        await websocket.accept()
        self.active_sessions[websocket] = container_id
        manager.add(websocket)

        # 🔎 Safe GHX log (connection open)
        if ENABLE_GLYPH_LOGGING:
            safe_ghx_log(
                ghx=None,
                evt={
                    "event": "ws_connected",
                    "container_id": container_id,
                    "scope": "ghx_ws",
                },
            )

        await self.send_initial_projection(websocket, container_id)

    async def send_initial_projection(self, websocket: WebSocket, container_id: str):
        try:
            container = load_container_by_id(container_id)
            ghx_packet = encode_glyphs_to_ghx(container)
            renderer = HolographicRenderer(ghx_packet)
            renderer.render_glyph_field()
            projection = renderer.export_projection()

            # 🔎 Safe GHX log (initial projection prepared)
            if ENABLE_GLYPH_LOGGING:
                safe_ghx_log(
                    ghx=renderer,
                    evt={
                        "event": "ghx_projection_prepared",
                        "container_id": container_id,
                        "payload_size": len(json.dumps(projection, default=str)) if projection else 0,
                    },
                )

            await websocket.send_text(json.dumps({
                "event": "ghx_projection",
                "container_id": container_id,
                "payload": projection
            }))

        except Exception as e:
            # 🔎 Safe GHX log (error path)
            if ENABLE_GLYPH_LOGGING:
                safe_ghx_log(
                    ghx=None,
                    evt={
                        "event": "ghx_error",
                        "container_id": container_id,
                        "error": str(e),
                        "stage": "send_initial_projection",
                    },
                )

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

                # 🔎 Safe GHX log (trigger attempt)
                if ENABLE_GLYPH_LOGGING:
                    safe_ghx_log(
                        ghx=renderer,
                        evt={
                            "event": "glyph_trigger_attempt",
                            "container_id": container_id,
                            "glyph_id": glyph_id,
                            "result": bool(triggered),
                        },
                    )

                if triggered:
                    await manager.broadcast(json.dumps({
                        "event": "glyph_triggered",
                        "glyph_id": glyph_id,
                        "activation": triggered
                    }))
        except Exception as e:
            # 🔎 Safe GHX log (error path)
            if ENABLE_GLYPH_LOGGING:
                safe_ghx_log(
                    ghx=None,
                    evt={
                        "event": "ghx_error",
                        "error": str(e),
                        "stage": "receive",
                    },
                )

            await websocket.send_text(json.dumps({
                "event": "ghx_error",
                "error": str(e)
            }))

    async def disconnect(self, websocket: WebSocket):
        container_id = self.active_sessions.get(websocket)
        if websocket in self.active_sessions:
            del self.active_sessions[websocket]
        manager.remove(websocket)

        # 🔎 Safe GHX log (connection closed)
        if ENABLE_GLYPH_LOGGING:
            safe_ghx_log(
                ghx=None,
                evt={
                    "event": "ws_disconnected",
                    "container_id": container_id,
                    "scope": "ghx_ws",
                },
            )


ghx_ws_handler = GHXWebSocketHandler()