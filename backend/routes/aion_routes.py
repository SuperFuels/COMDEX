from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.modules.consciousness.state_manager import state_manager

router = APIRouter()

class GlyphMutationRequest(BaseModel):
    coord: str
    glyph: str

@router.post("/api/aion/mutate-glyph")
async def mutate_glyph(req: GlyphMutationRequest):
    container = state_manager.get_current_container()
    if not container:
        return {"error": "No container loaded"}
    
    if req.coord not in container["cubes"]:
        container["cubes"][req.coord] = {}

    container["cubes"][req.coord]["glyph"] = req.glyph

    # Optional: mark cube as modified
    container["cubes"][req.coord]["mutated"] = True

    return {"status": "ok", "coord": req.coord, "glyph": req.glyph}