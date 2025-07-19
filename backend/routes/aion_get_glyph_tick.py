# backend/routes/aion_get_glyph_tick.py

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from backend.modules.runtime.container_runtime import get_container_runtime

router = APIRouter()

@router.get("/api/aion/glyphs")
async def get_glyphs_at_tick(t: int = Query(..., description="Tick index to fetch rewind state")):
    runtime = get_container_runtime()
    if not runtime or not hasattr(runtime, "rewind_buffer"):
        return JSONResponse({"error": "Container runtime or rewind buffer not available"}, status_code=500)

    if t < 0 or t >= len(runtime.rewind_buffer):
        return JSONResponse({"error": f"Invalid tick {t}, available range: 0–{len(runtime.rewind_buffer) - 1}"}, status_code=400)

    state = runtime.rewind_buffer[t]
    return {"tick": t, "cubes": state.get("cubes", {}), "glyphs": list(state.get("cubes", {}).values())}