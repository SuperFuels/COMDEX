# File: backend/routes/aion_get_glyph_tick.py

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from backend.modules.runtime.container_runtime import get_container_runtime

router = APIRouter()

@router.get("/api/aion/glyphs")
async def get_glyphs_at_tick(
    t: int = Query(..., description="Tick index to fetch rewind state")
):
    runtime = get_container_runtime()

    if not runtime or not hasattr(runtime, "rewind_buffer"):
        return JSONResponse(
            {"error": "Container runtime or rewind buffer not available"},
            status_code=500
        )

    total_ticks = len(runtime.rewind_buffer)
    if t < 0 or t >= total_ticks:
        return JSONResponse(
            {
                "error": f"Invalid tick {t}. Valid range: 0 to {total_ticks - 1}",
                "available_ticks": total_ticks
            },
            status_code=400
        )

    state = runtime.rewind_buffer[t]
    cubes = state.get("cubes", {})

    glyphs = [
        cube for cube in cubes.values()
        if "glyph" in cube or "glyphs" in cube
    ]

    return {
        "tick": t,
        "total_ticks": total_ticks,
        "count": len(glyphs),
        "glyphs": sorted(glyphs, key=lambda g: g.get("coord", ""))
    }