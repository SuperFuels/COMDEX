# 📁 backend/routes/aion_synthesize_glyphs.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from backend.modules.glyphos.glyph_synthesis_engine import synthesize_glyphs_from_text
from backend.modules.dna_chain.dc_handler import inject_glyphs_into_container

import traceback
import logging

router = APIRouter()

class SynthesisRequest(BaseModel):
    input: str
    source: Optional[str] = "manual"
    inject_to_grid: Optional[bool] = False
    container: Optional[str] = None  # e.g. "glyph_synthesis_lab.dc.json"

class SynthesisResponse(BaseModel):
    success: bool
    glyphs: List[dict]
    injected: bool = False
    container: Optional[str] = None
    error: Optional[str] = None  # new field for frontend debug

@router.post("/api/aion/synthesize-glyphs", response_model=SynthesisResponse)
async def synthesize_glyphs(request: SynthesisRequest):
    try:
        # Step 1: Synthesize glyphs from input
        glyphs = synthesize_glyphs_from_text(request.input, source=request.source)

        injected = False

        # Step 2: Optional grid injection
        if request.inject_to_grid and request.container:
            injected = inject_glyphs_into_container(
                container_filename=request.container,
                glyphs=glyphs,
                source=request.source
            )

        return SynthesisResponse(
            success=True,
            glyphs=glyphs,
            injected=injected,
            container=request.container if injected else None
        )

    except Exception as e:
        logging.error("Glyph synthesis failed:")
        traceback.print_exc()

        # Optional fallback for frontend dev
        fallback_glyph = {
            "symbol": "✦",
            "meaning": "Milestone",
            "source": "fallback",
            "confidence": 0.5,
        }

        return SynthesisResponse(
            success=False,
            glyphs=[fallback_glyph],
            injected=False,
            error=str(e)
        )