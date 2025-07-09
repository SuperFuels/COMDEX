from fastapi import APIRouter
from pydantic import BaseModel
from backend.modules.consciousness.state_manager import STATE

router = APIRouter()

class GlyphMutationRequest(BaseModel):
    coord: str
    glyph: str

@router.post("/api/aion/mutate-glyph")
async def mutate_glyph(req: GlyphMutationRequest):
    container = STATE.get_current_container()
    if not container:
        return {"error": "No container loaded"}
    
    if "cubes" not in container:
        container["cubes"] = {}

    if req.coord not in container["cubes"]:
        container["cubes"][req.coord] = {}

    container["cubes"][req.coord]["glyph"] = req.glyph
    container["cubes"][req.coord]["mutated"] = True  # Optional mutation marker

    return {
        "status": "ok",
        "coord": req.coord,
        "glyph": req.glyph
    }