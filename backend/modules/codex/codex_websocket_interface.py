# 📁 codex_websocket_interface.py

import asyncio
import websockets
import json
import traceback

from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.hexcore.memory_engine import MEMORY

connected_clients = set()
codex = CodexCore()
metrics = CodexMetrics()
tessaris = TessarisEngine()
cost_estimator = CodexCostEstimator()

async def broadcast_glyph_execution(glyph, result, context):
    cost_obj = cost_estimator.estimate_glyph_cost(glyph, context or {})
    cost = cost_obj.total()
    detail = {
        "energy": cost_obj.energy,
        "ethics_risk": cost_obj.ethics_risk,
        "delay": cost_obj.delay,
        "opportunity_loss": cost_obj.opportunity_loss
    }

    payload = {
        "type": "glyph_execution",
        "payload": {
            "glyph": glyph,
            "action": result,
            "source": context.get("source", "unknown"),
            "timestamp": asyncio.get_event_loop().time(),
            "cost": cost,
            "detail": detail
        }
    }
    message = json.dumps(payload)
    for client in connected_clients.copy():
        try:
            await client.send(message)
        except:
            connected_clients.discard(client)

async def codex_handler(websocket, path):
    connected_clients.add(websocket)
    print(f"🌐 Codex WebSocket connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)

                if "glyph" in data:
                    glyph = data["glyph"]
                    context = data.get("context", {})
                    metadata = data.get("metadata", {})

                    result = codex.execute(glyph, context)
                    metrics.record_execution()

                    MEMORY.store({
                        "label": "codex_ws_execution",
                        "type": "websocket_glyph",
                        "glyph": glyph,
                        "context": context,
                        "result": result
                    })

                    tessaris.extract_intents_from_glyphs([glyph], metadata)

                    await broadcast_glyph_execution(glyph, result, context)

                    await websocket.send(json.dumps({
                        "status": "ok",
                        "glyph": glyph,
                        "result": result
                    }))

                elif "command" in data and data["command"] == "observe":
                    await websocket.send(json.dumps({
                        "status": "ok",
                        "message": "Observer hook not yet implemented"
                    }))

                else:
                    await websocket.send(json.dumps({
                        "status": "error",
                        "error": "Invalid request: no glyph or command"
                    }))

            except Exception as e:
                tb = traceback.format_exc()
                await websocket.send(json.dumps({
                    "status": "error",
                    "error": str(e),
                    "trace": tb
                }))

    finally:
        connected_clients.remove(websocket)
        print(f"🔌 Codex WebSocket disconnected: {websocket.remote_address}")

# ✅ Fix: make this a coroutine that waits for shutdown
async def start_codex_ws_server():
    print("🌐 Codex WebSocket server starting on ws://localhost:8671")
    server = await websockets.serve(codex_handler, "localhost", 8671)
    await server.wait_closed()