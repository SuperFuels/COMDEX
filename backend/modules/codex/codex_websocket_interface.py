# 📁 backend/modules/codex/codex_websocket_interface.py

import json
import traceback
from fastapi import WebSocket, WebSocketDisconnect

from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.codex.codex_emulator import CodexEmulator
from backend.modules.glyphos.codexlang_translator import run_codexlang_string
from backend.modules.hexcore.memory_engine import MEMORY

# 🛰️ Lazy import dispatcher to break circular import
def _get_handle_glyphnet_event():
    from backend.routes.ws.glyphnet_ws import handle_glyphnet_event
    return handle_glyphnet_event

# ✅ Runtime Instances
connected_clients = set()
codex = CodexCore()
emulator = CodexEmulator()
metrics = CodexMetrics()
tessaris = None  # ✅ Lazy init to prevent circular import
cost_estimator = CodexCostEstimator()


def _get_tessaris():
    """Lazily import TessarisEngine to avoid circular import."""
    global tessaris
    if tessaris is None:
        from backend.modules.tessaris.tessaris_engine import TessarisEngine
        tessaris = TessarisEngine()
    return tessaris


# ✅ Broadcast to all clients
async def broadcast_glyph_execution(glyph, result, context):
    cost_obj = cost_estimator.estimate_glyph_cost(glyph, context or {})
    cost = cost_obj.total()
    detail = {
        "energy": cost_obj.energy,
        "ethics_risk": cost_obj.ethics_risk,
        "delay": cost_obj.delay,
        "opportunity_loss": cost_obj.opportunity_loss,
    }

    payload = {
        "type": "glyph_execution",
        "payload": {
            "glyph": glyph,
            "action": result,
            "source": context.get("source", "unknown"),
            "timestamp": context.get("timestamp"),
            "cost": cost,
            "detail": detail,
        },
    }

    message = json.dumps(payload)
    for client in connected_clients.copy():
        try:
            await client.send_text(message)
        except:
            connected_clients.discard(client)


# ✅ WebSocket Handler
async def codex_ws_handler(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print("🌐 Codex WebSocket connected")

    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)

                # 🛰️ Remote glyph trigger support
                if data.get("event") == "trigger_glyph":
                    await _get_handle_glyphnet_event()(websocket, data)
                    continue

                glyph = data.get("glyph")
                scroll = data.get("scroll")
                context = data.get("context", {})
                metadata = data.get("metadata", {})

                # 🧠 Execute single glyph
                if glyph:
                    result = codex.execute(glyph, context)
                    metrics.record_execution()

                    MEMORY.store({
                        "label": "codex_ws_execution",
                        "type": "websocket_glyph",
                        "glyph": glyph,
                        "context": context,
                        "result": result,
                    })

                    # ✅ Tessaris alignment (photon-aware)
                    origin = context.get("source", "codex")
                    if origin == "photon":
                        _get_tessaris().extract_intents_from_glyphs(
                            [glyph],
                            {**metadata, "origin": "photon"}
                        )
                    else:
                        _get_tessaris().extract_intents_from_glyphs([glyph], metadata)

                    await broadcast_glyph_execution(glyph, result, {**context, "source": origin})

                    await websocket.send_text(json.dumps({
                        "status": "ok",
                        "glyph": glyph,
                        "result": result,
                        "origin": origin,
                    }))

                # 🌀 Execute CodexLang scroll
                elif scroll:
                    # ✅ Force photon tag if declared in metadata
                    origin = metadata.get("origin", "codex")
                    if origin == "photon":
                        metadata["origin"] = "photon"

                    result = emulator.run(scroll, context)

                    MEMORY.store({
                        "label": "codex_scroll_execution",
                        "type": "scroll",
                        "scroll": scroll,
                        "result": result,
                    })

                    # ✅ Photon Tessaris alignment
                    if origin == "photon":
                        _get_tessaris().extract_intents_from_glyphs(
                            result if isinstance(result, list) else [scroll],
                            {**metadata, "origin": "photon"}
                        )

                    await websocket.send_text(json.dumps({
                        "status": "ok",
                        "scroll": scroll,
                        "result": result,
                        "origin": origin,
                    }))

                else:
                    await websocket.send_text(json.dumps({
                        "status": "error",
                        "error": "Invalid request: must provide glyph or scroll"
                    }))

            except Exception as e:
                await websocket.send_text(json.dumps({
                    "status": "error",
                    "error": str(e),
                    "trace": traceback.format_exc()
                }))

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print("🔌 Codex WebSocket disconnected")


# ✅ Minimal stub for FastAPI compatibility
async def start_codex_ws_server(websocket: WebSocket):
    await codex_ws_handler(websocket)


# ✅ Fallback CLI/Test compatible event stub
async def send_codex_ws_event(event_type: str, payload: dict):
    message = json.dumps({
        "type": event_type,
        "payload": payload,
    })

    for client in connected_clients.copy():
        try:
            await client.send_text(message)
        except:
            connected_clients.discard(client)


import asyncio

def send_codex_ws_event_sync(event_type: str, payload: dict):
    """
    Schedule a websocket event send, safe in both async and sync contexts.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(send_codex_ws_event(event_type, payload))
        else:
            loop.run_until_complete(send_codex_ws_event(event_type, payload))
    except Exception as e:
        print(f"⚠️ WS broadcast skipped: {e}")

# ✅ New: safe, non-circular tick broadcaster
def broadcast_tick(data: dict):
    """
    Lightweight tick broadcaster used by CodexFabric and Scheduler loops.
    Avoids circular imports by dispatching through send_codex_ws_event_sync lazily.
    """
    try:
        # direct reference instead of re-importing
        send_codex_ws_event_sync("tick", data)
    except Exception as e:
        print(f"[WS] Tick broadcast failed: {e}")