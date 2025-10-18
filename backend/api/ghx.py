from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import asyncio, json
from backend.modules.cognitive_fabric.ghx_telemetry_adapter import GHX_TELEMETRY

router = APIRouter()

@router.get("/ghx/stream")
async def ghx_stream():
    async def event_generator():
        while True:
            payload = GHX_TELEMETRY.latest_payload()
            if payload:
                yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(5)
    return EventSourceResponse(event_generator())