# WebSocket interface for generating and collapsing QGlyphs on demand

import json
from fastapi import WebSocket, WebSocketDisconnect
from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore

clients = set()

async def qglyph_ws_handler(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    core = GlyphQuantumCore(container_id="main")

    print("🌐 QGlyph WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            action = data.get("action")
            glyph = data.get("glyph", "⊕")
            coord = data.get("coord", "0x0")

            if action == "generate":
                qbit = core.generate_qbit(glyph, coord)
                await websocket.send_json({"status": "ok", "qbit": qbit})
            elif action == "collapse":
                qbit = data.get("qbit")
                if qbit:
                    result = core.collapse_qbit(qbit)
                    await websocket.send_json({"status": "ok", "collapsed": result})
                else:
                    await websocket.send_json({"status": "error", "message": "Missing qbit for collapse."})
            else:
                await websocket.send_json({"status": "error", "message": f"Invalid action: {action}"})
    except WebSocketDisconnect:
        clients.discard(websocket)
        print("🔌 QGlyph WebSocket disconnected")