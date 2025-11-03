# backend/api/ghx.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse
import asyncio, time, json

# optional live source
try:
    from backend.modules.cognitive_fabric.ghx_telemetry_adapter import GHX_TELEMETRY  # type: ignore
except Exception:
    GHX_TELEMETRY = None

# HTTP/SSE router
router = APIRouter(tags=["GHX"])

@router.get("/ghx/stream")
async def ghx_stream():
    async def event_generator():
        while True:
            if GHX_TELEMETRY:
                payload = GHX_TELEMETRY.latest_payload() or {"type": "heartbeat", "ts": time.time()}
            else:
                payload = {"type": "heartbeat", "ts": time.time()}
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(5)
    return EventSourceResponse(event_generator())

# WebSocket router
ws_router = APIRouter()

@ws_router.websocket("/ws/ghx/{container_id}")
async def ghx_feed(ws: WebSocket, container_id: str):
    await ws.accept()
    try:
        i = 0
        while True:
            i += 1
            await ws.send_json({"type": "heartbeat", "container_id": container_id, "seq": i, "ts": time.time()})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass