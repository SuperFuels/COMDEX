# 📁 backend/modules/codex/codex_websocket_interface.py

import json
import traceback
from fastapi import WebSocket, WebSocketDisconnect

from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.hexcore.memory_engine import MEMORY

# ✅ Runtime Instances
connected_clients = set()
codex = CodexCore()
metrics = CodexMetrics()
tessaris = TessarisEngine()
cost_estimator = CodexCostEstimator()

# ✅ Broadcast execution trace to all clients
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
            "timestamp": context.get("timestamp"),
            "cost": cost,
            "detail": detail
        }
    }

    message = json.dumps(payload)
    for client in connected_clients.copy():
        try:
            await client.send_text(message)
        except:
            connected_clients.discard(client)

# ✅ FastAPI-compatible WebSocket handler
async def codex_ws_handler(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print("🌐 Codex WebSocket connected")

    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                glyph = data.get("glyph")
                context = data.get("context", {})
                metadata = data.get("metadata", {})

                if glyph:
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

                    await websocket.send_text(json.dumps({
                        "status": "ok",
                        "glyph": glyph,
                        "result": result
                    }))

                elif data.get("command") == "observe":
                    await websocket.send_text(json.dumps({
                        "status": "ok",
                        "message": "Observer hook not yet implemented"
                    }))

                else:
                    await websocket.send_text(json.dumps({
                        "status": "error",
                        "error": "Invalid request: no glyph or command"
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