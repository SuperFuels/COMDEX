from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import json

from backend.modules.websocket_manager import websocket_manager
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.dna_chain.dc_handler import get_dc_path, load_dc_container, save_dc_container

DNA_SWITCH.register(__file__)
router = APIRouter()

class GlyphMutationRequest(BaseModel):
    container_id: str
    coord: str  # e.g., "x1_y2_z0"
    glyph: str  # e.g., "🧠", "⚙", etc.

@router.post("/aion/glyph/mutate")
async def mutate_glyph(req: GlyphMutationRequest):
    try:
        path = get_dc_path(req.container_id)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Container '{req.container_id}' not found")

        container = load_dc_container(req.container_id)

        # Get or create the target cube
        cube = container.setdefault("cubes", {}).setdefault(req.coord, {})
        cube["glyph"] = req.glyph
        cube["mutated"] = True
        cube["last_modified"] = datetime.utcnow().isoformat()

        save_dc_container(req.container_id, container)

        # Log in memory
        store_memory({
            "type": "glyph_mutation",
            "container": req.container_id,
            "coord": req.coord,
            "glyph": req.glyph,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Broadcast glyph update
        await websocket_manager.broadcast({
            "type": "glyph_update",
            "coord": req.coord,
            "glyph": req.glyph,
            "container_id": req.container_id,
        })

        return {"status": "ok", "message": f"Glyph {req.glyph} updated at {req.coord}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))