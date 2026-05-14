# -*- coding: utf-8 -*-
# backend/routes/aion_routes.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

from backend.modules.consciousness.state_manager import STATE

router = APIRouter(prefix="/api/aion", tags=["AION"])


# ---------- Models ----------
class GlyphMutationRequest(BaseModel):
    coord: str
    glyph: str


# ---------- Endpoints ----------
@router.post("/mutate-glyph")
async def mutate_glyph(req: GlyphMutationRequest) -> Dict[str, Any]:
    """
    Mutate a glyph in the active AION container at the given coordinate.
    Ensures cubes and slots exist, then marks the glyph as mutated.
    """
    container = STATE.get_current_container()
    if not container:
        return {"error": "No container loaded"}

    # Ensure cubes structure
    cubes = container.setdefault("cubes", {})
    cube = cubes.setdefault(req.coord, {})

    # Apply mutation
    cube["glyph"] = req.glyph
    cube["mutated"] = True  # Optional mutation marker

    return {
        "status": "ok",
        "coord": req.coord,
        "glyph": req.glyph,
    }