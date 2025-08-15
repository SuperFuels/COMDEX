# File: backend/modules/holograms/ghx_ws_interface.py
# (If your file currently lives under `hologram/`, move it into `holograms/` to match package layout.)

import json
import logging
from fastapi import WebSocket, WebSocketDisconnect

# ✅ WebSocket manager import (supports both `manager` alias and raw singleton)
try:
    from backend.modules.websocket_manager import manager
except Exception:
    # Fallback if only `websocket_manager` is exported
    from backend.modules.websocket_manager import websocket_manager as manager  # type: ignore

# ✅ Hologram/HGX imports (plural package name)
try:
    from backend.modules.holograms.holographic_renderer import HolographicRenderer
except Exception:
    # Relative fallback if path changes inside the package
    from .holographic_renderer import HolographicRenderer  # type: ignore

try:
    from backend.modules.holograms.ghx_encoder import encode_glyphs_to_ghx
except Exception:
    from .ghx_encoder import encode_glyphs_to_ghx  # type: ignore

# ✅ Container loader: prefer state manager if present, else use UCS runtime as a safe fallback
def _resolve_load_container_by_id():
    try:
        # If you actually have a state manager, this will be used.
        from backend.modules.state.state_manager import load_container_by_id  # type: ignore
        return load_container_by_id
    except Exception:
        try:
            # UCS fallback (ships in your tree)
            from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime  # type: ignore

            def load_container_by_id(container_id: str):
                ucs = get_ucs_runtime()
                # Try exact name, else return active container
                try:
                    return ucs.get_container(container_id)
                except Exception:
                    return ucs.get_active_container()

            return load_container_by_id
        except Exception:
            # Ultra-safe stub so the WS doesn’t hard-crash; you can replace with a hard error if preferred.
            def load_container_by_id(_container_id: str):
                return {}

            return load_container_by_id


load_container_by_id = _resolve_load_container_by_id()

# ✅ Optional: respect backend config flag for GHX logging
try:
    from backend.config import ENABLE_GLYPH_LOGGING
except Exception:
    ENABLE_GLYPH_LOGGING = True  # safe default

# ✅ Optional: safe GHX log shim — never raises even if interface changes
try:
    from backend.modules.holograms.ghx_logging import safe_ghx_log  # plural path
except Exception:
    try:
        from backend.modules.hologram.ghx_logging import safe_ghx_log  # singular fallback if it exists
    except Exception:
        def safe_ghx_log(ghx, evt):
            try:
                logging.debug("[GHX][safe_ghx_log fallback] %s", evt)
            except Exception:
                pass


class GHXWebSocketHandler:
    def __init__(self):
        self.active_sessions = {}

    async def connect(self, websocket: WebSocket, container_id: str):
        await websocket.accept()
        self.active_sessions[websocket] = container_id
        try:
            manager.add(websocket)  # your manager exposes add/remove/broadcast
        except Exception:
            # If your manager uses different API (e.g., connect/disconnect), fall back
            try:
                await manager.connect(websocket)  # type: ignore
            except Exception:
                logging.warning("[GHX] WebSocket manager has no add/connect")

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
                    # Try manager.broadcast(text)
                    try:
                        await manager.broadcast(json.dumps({
                            "event": "glyph_triggered",
                            "glyph_id": glyph_id,
                            "activation": triggered
                        }))
                    except Exception:
                        # Fallback to a tag-based broadcast signature if that’s what you use
                        try:
                            await manager.broadcast(
                                {"event": "glyph_triggered", "glyph_id": glyph_id, "activation": triggered},
                                tag="ghx"
                            )  # type: ignore
                        except Exception as be:
                            logging.warning("[GHX] Broadcast failed: %s", be)

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

        try:
            manager.remove(websocket)
        except Exception:
            try:
                await manager.disconnect(websocket)  # type: ignore
            except Exception:
                logging.warning("[GHX] WebSocket manager has no remove/disconnect")

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