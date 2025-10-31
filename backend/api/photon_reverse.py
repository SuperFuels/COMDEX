# backend/api/photon_reverse.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json

from backend.modules.glyphos.glyph_storage import get_glyph_registry
from backend.modules.glyphos.glyph_utils import expand_from_glyphs

router = APIRouter(prefix="/api/photon", tags=["photon"])

class ReverseRequest(BaseModel):
    glyphs: List[str]
    mode: Optional[str] = "auto"  # "registry" | "expand" | "auto"

@router.post("/translate_reverse")
async def translate_reverse(body: ReverseRequest):
    registry = get_glyph_registry()
    out = []
    for g in body.glyphs:
        if body.mode in ("registry", "auto"):
            lemmas = [k for k, v in registry.items() if isinstance(v, dict) and v.get("glyph") == g]
            if lemmas:
                out.append({"glyph": g, "text": lemmas[0], "source": "registry"})
                continue
        # fallback
        expanded = expand_from_glyphs([g])
        out.append({"glyph": g, "text": expanded, "source": "expand"})
    return {"status": "ok", "items": out}

@router.post("/translate_reverse_file")
async def translate_reverse_file(file: UploadFile = File(...)):
    try:
        capsule = json.loads((await file.read()).decode("utf-8", errors="ignore"))
        glyphs = capsule.get("glyphs", [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid .photon file: {e}")

    registry = get_glyph_registry()
    items = []
    for g in glyphs:
        lemmas = [k for k, v in registry.items() if isinstance(v, dict) and v.get("glyph") == g]
        text = lemmas[0] if lemmas else expand_from_glyphs([g])
        items.append({"glyph": g, "text": text})
    return {
        "status": "ok",
        "source_file": getattr(file, "filename", None),
        "items": items,
        "joined_text": "\n".join(i["text"] for i in items)
    }