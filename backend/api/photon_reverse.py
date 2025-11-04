# backend/api/photon_reverse.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, model_validator

from backend.modules.photon.validation import validate_photon_capsule
from backend.modules.glyphos.glyph_storage import get_glyph_registry
from backend.modules.glyphos.glyph_utils import expand_from_glyphs

router = APIRouter(prefix="/api/photon", tags=["PhotonLang"])

# ---- Request model that allows either capsule OR glyphs ----------------------
class ReverseRequest(BaseModel):
    capsule: Optional[Dict[str, Any]] = None
    glyphs: Optional[List[Any]] = None
    mode: Optional[str] = "auto"  # "registry" | "expand" | "auto"

    @model_validator(mode="after")
    def ensure_one_present(self) -> "ReverseRequest":
        if self.capsule is None and self.glyphs is None:
            raise ValueError("Provide either 'capsule' or 'glyphs'.")
        return self

# ---- Helpers ----------------------------------------------------------------
def _extract_glyph_items(capsule: Dict[str, Any]) -> List[Any]:
    """
    Accepts both 'glyph_stream' and 'glyphs', each containing either strings
    or glyph dicts. Returns a flat list of items we can resolve to text.
    """
    items = capsule.get("glyph_stream") or capsule.get("glyphs") or []
    if not isinstance(items, list):
        return []
    return items

def _glyph_to_key(item: Any) -> str:
    """
    Normalize a glyph item (str or dict) into a lookup key:
    - string: return as-is
    - dict: prefer 'expr', then 'symbol', then 'operator'
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if isinstance(item.get("expr"), str):
            return item["expr"]
        if isinstance(item.get("symbol"), str):
            return item["symbol"]
        if isinstance(item.get("operator"), str):
            # Turn operator + optional args into a compact signature
            args = item.get("args") or []
            try:
                arg_str = ",".join(json.dumps(a, ensure_ascii=False) for a in args)
                return f"{item['operator']}({arg_str})" if args else item["operator"]
            except Exception:
                return item["operator"]
    return json.dumps(item, ensure_ascii=False)

def _resolve_text_for_glyph(glyph_key: str, registry: Dict[str, Any], mode: str) -> str:
    """
    Try registry lemma; if absent or mode forces, fallback to expand_from_glyphs.
    """
    if mode in ("registry", "auto"):
        # Registry entries look like: { "lemma": { "glyph": "✦", ... }, ... }
        for lemma, entry in registry.items():
            if isinstance(entry, dict) and entry.get("glyph") == glyph_key:
                return str(lemma)
        # If glyph_key itself is a known lemma, return as-is
        if glyph_key in registry:
            return str(glyph_key)

    # Fallback: expansion
    try:
        return expand_from_glyphs([glyph_key])
    except Exception:
        return glyph_key  # last resort: echo back

def _reverse_items(items: List[Any], mode: str) -> List[Dict[str, str]]:
    registry = get_glyph_registry()
    out: List[Dict[str, str]] = []
    for it in items:
        gkey = _glyph_to_key(it)
        text = _resolve_text_for_glyph(gkey, registry, mode)
        out.append({"glyph": gkey, "text": text})
    return out

# ---- Routes -----------------------------------------------------------------
@router.post("/translate_reverse")
async def translate_reverse(body: ReverseRequest):
    try:
        if body.capsule is not None:
            capsule = dict(body.capsule)
            # validate full capsule (supports glyphs OR glyph_stream)
            validate_photon_capsule(capsule)
            items = _extract_glyph_items(capsule)
            rev = _reverse_items(items, body.mode or "auto")
            return {
                "status": "ok",
                "items": rev,
                "joined_text": "\n".join(x["text"] for x in rev),
                "name": capsule.get("name"),
                "engine": capsule.get("engine"),
            }

        # Else: raw glyph list (strings or dicts)
        glyphs = list(body.glyphs or [])
        rev = _reverse_items(glyphs, body.mode or "auto")
        return {
            "status": "ok",
            "items": rev,
            "joined_text": "\n".join(x["text"] for x in rev),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Reverse translation failed: {e}")

@router.post("/translate_reverse_file")
async def translate_reverse_file(file: UploadFile = File(...)):
    try:
        raw = (await file.read()).decode("utf-8", errors="ignore")
        capsule = json.loads(raw)
        validate_photon_capsule(capsule)

        items = _extract_glyph_items(capsule)
        rev = _reverse_items(items, mode="auto")
        return {
            "status": "ok",
            "source_file": getattr(file, "filename", None),
            "items": rev,
            "joined_text": "\n".join(x["text"] for x in rev),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid photon capsule: {e}")