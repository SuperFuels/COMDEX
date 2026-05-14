from fastapi import APIRouter
from backend.photon.lexer import text_to_glyphs
from backend.modules.aion_language.sci_bridge import emit_sci_event

router = APIRouter()

@router.post("/photon/ingest_text")
async def ingest(payload: dict):
    text = payload.get("text", "")
    glyphs = text_to_glyphs(text)
    
    # broadcast to SCI stream
    emit_sci_event("glyph_stream", {"glyphs": glyphs, "raw": text})
    
    return {"ok": True, "glyphs": glyphs}