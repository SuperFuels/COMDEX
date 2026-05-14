# File: backend/routes/aion_phi_stream.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio, json, time
from backend.modules.aion_resonance.resonance_state import load_phi_state

router = APIRouter()

# Connection pool (optional future multi-client broadcast)
active_connections = set()

@router.websocket("/phi-stream")
async def phi_stream(ws: WebSocket):
    """
    Real-time Φ telemetry stream.
    Sends JSON packets every 2 seconds containing coherence, entropy, flux, and load.
    """
    await ws.accept()
    active_connections.add(ws)
    print("[Φ-Stream] Client connected.")

    try:
        while True:
            state = load_phi_state() or {}
            state["timestamp_readable"] = time.strftime("%H:%M:%S")
            packet = {
                "type": "phi_update",
                "state": state,
            }
            await ws.send_text(json.dumps(packet, indent=2))
            await asyncio.sleep(2.0)  # update interval
    except WebSocketDisconnect:
        print("[Φ-Stream] Client disconnected.")
    finally:
        active_connections.remove(ws)