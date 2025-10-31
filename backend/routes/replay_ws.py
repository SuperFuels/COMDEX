# backend/routes/replay_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.AION.trace_bus import subscribe
import asyncio

# WebSocket route under /api
router = APIRouter(prefix="/api", tags=["Replay"])

clients = set()

async def broadcast(evt: dict):
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(evt)
        except Exception:
            dead.append(ws)
    for d in dead:
        clients.discard(d)

# Trace event hook → broadcast to WS listeners
def hook(evt):
    # ensure safe async scheduling (inside FastAPI loop)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast(evt))
    except RuntimeError:
        # no loop running yet — schedule later
        asyncio.get_event_loop().create_task(broadcast(evt))

# Subscribe once on import
subscribe(hook)

@router.websocket("/ws/replay")
async def replay_ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            # Client does not send anything — just keep alive
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)
    except Exception:
        clients.discard(ws)