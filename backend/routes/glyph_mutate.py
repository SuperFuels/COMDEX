from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import json

from backend.modules.websocket_manager import websocket_manager
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.dna_chain.dc_handler import (
    get_dc_path,
    load_dc_container,
    save_dc_container
)

DNA_SWITCH.register(__file__)
router = APIRouter()

# You can extend this set
VALID_GLYPHS = {"🧠", "⚙", "✧", "✦", "⬁", "🧬", "⟲", "⧉", "🪄", "🪞", "🧽", "⚛", "→", "↔"}

class GlyphMutationRequest(BaseModel):
    container_id: str
    coord: str  # e.g., "x1_y2_z0"
    glyph: str  # e.g., "🧠", "⚙", etc.

@router.post("/aion/glyph/mutate")
async def mutate_glyph(req: GlyphMutationRequest):
    try:
        if req.glyph not in VALID_GLYPHS:
            raise HTTPException(status_code=400, detail=f"Invalid glyph: {req.glyph}")

        path = get_dc_path(req.container_id)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Container '{req.container_id}' not found")

        container = load_dc_container(req.container_id)

        cubes = container.setdefault("cubes", {})
        cube = cubes.setdefault(req.coord, {})

        previous_glyph = cube.get("glyph", None)

        # Update glyph
        cube["glyph"] = req.glyph
        cube["mutated"] = True
        cube["last_modified"] = datetime.utcnow().isoformat()

        # Save updated container
        save_dc_container(req.container_id, container)

        # Log memory event
        store_memory({
            "type": "glyph_mutation",
            "container": req.container_id,
            "coord": req.coord,
            "glyph": req.glyph,
            "previous": previous_glyph,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Broadcast update with diff info
        await websocket_manager.broadcast({
            "type": "glyph_update",
            "coord": req.coord,
            "glyph": req.glyph,
            "previous": previous_glyph,
            "container_id": req.container_id,
        })

        return {
            "status": "ok",
            "message": f"Glyph {req.glyph} updated at {req.coord}",
            "previous": previous_glyph
        }

    except Exception as e:
        if hasattr(DNA_SWITCH, "log_exception"):
            DNA_SWITCH.log_exception(e)
        raise HTTPException(status_code=500, detail=str(e))