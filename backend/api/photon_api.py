from __future__ import annotations
# 📁 backend/api/photon_api.py
print("🛰️ [Photon API] Initializing PhotonLang routes...")

"""
PhotonLang API
──────────────────────────────────────────────
Provides endpoints for:
- Translating PhotonLang to glyph-plane form
- Compiling PhotonLang source
- Executing glyph code through Photon-Symatics Bridge
- Reverse translation: Photon capsule → PhotonLang
"""

import json
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel

# ✅ Core imports
from backend.modules.photonlang.photon_translator import PhotonTranslator
from backend.modules.photon.validation import validate_photon_capsule

try:
    from backend.symatics.photon_symatics_bridge import PhotonSymaticsBridge
except ModuleNotFoundError as e:
    print(f"⚠️ [Photon API] Bridge import failed: {e}")
    PhotonSymaticsBridge = None

# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/photon", tags=["PhotonLang"])
translator = PhotonTranslator()
bridge = PhotonSymaticsBridge() if PhotonSymaticsBridge else None

# ─────────────────────────────────────────────────────────────────────────────
# 📦 Request Models (only where we want OpenAPI schemas)
# ─────────────────────────────────────────────────────────────────────────────
class TranslateLineRequest(BaseModel):
    line: str

class CompileFileRequest(BaseModel):
    path: str

# ─────────────────────────────────────────────────────────────────────────────
# 🌊 Translate a single PhotonLang line -> glyphs
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/translate_line")
async def translate_line(req: TranslateLineRequest):
    try:
        result = translator.translate_line(req.line)
        return {"input": req.line, "translated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 📜 Translate multi-line PhotonLang block -> glyphs
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/translate_block")
async def translate_block(request: Request):
    data = await request.json()
    source = data.get("source", "")
    if not source.strip():
        return {"translated": ""}

    lines = source.splitlines()
    translated_lines = []
    for line in lines:
        try:
            if line.strip():
                translated_lines.append(translator.translate_line(line))
            else:
                translated_lines.append("")
        except Exception as e:
            translated_lines.append(f"# ⚠️ Error: {e}")

    return {"translated": "\n".join(translated_lines)}

# ─────────────────────────────────────────────────────────────────────────────
# ⚛ Execute glyph-plane or PhotonLang source via Photon-Symatics Bridge
# ─────────────────────────────────────────────────────────────────────────────
print("🛰️ [Photon API] Router active -> /api/photon/execute_raw")

@router.post("/execute_raw")
async def execute_raw(payload: Dict[str, Any]):
    """
    Executes either:
      - Raw PhotonLang code (💡 = 🌊 ⊕ 🌀)
      - Pre-compiled glyph capsules
    through the Photon-Symatics Bridge, auto-translating as needed.
    """
    if bridge is None:
        raise HTTPException(status_code=500, detail="PhotonSymaticsBridge unavailable.")

    try:
        source = payload.get("source")
        if not source:
            raise HTTPException(status_code=400, detail="Missing 'source' field")

        # 🧩 Auto-translate raw PhotonLang -> capsule
        if isinstance(source, str):
            print(f"💡 [Photon API] Translating PhotonLang source: {source}")
            translated = translator.translate_line(source)
            capsule = {
                "name": "bridge_capsule",
                "glyphs": [translated] if isinstance(translated, dict) else [{"expr": translated}],
            }
        elif isinstance(source, dict) and "glyphs" in source:
            capsule = source
        else:
            raise HTTPException(status_code=400, detail="Invalid source format; must be string or capsule object.")

        # 🚀 Execute through Photon-Symatics Bridge
        results = await bridge.execute_raw(capsule)
        return results

    except Exception as e:
        print(f"⚠️ [Photon API] execute_raw error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 🧩 Compile a Photon source file -> symbolic structure
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/compile_file")
async def compile_file(req: CompileFileRequest):
    try:
        compiled = translator.compile_file(req.path)
        return {"status": "ok", "compiled": compiled}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {req.path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 🔁 Reverse translation helpers (capsule -> PhotonLang text)
# ─────────────────────────────────────────────────────────────────────────────
def _glyph_to_photon_line(g: Dict[str, Any]) -> str:
    """
    Very simple, readable formatter from a glyph item to PhotonLang-like syntax.
    Expected glyph keys: operator, args (list), optional name/logic.
    """
    op = g.get("operator") or g.get("symbol") or "⊕"
    args = g.get("args") or []

    def s(x: Any) -> str:
        if isinstance(x, str):
            # quote if it contains spaces or non-alnum (keeps operators readable)
            return x if x.isidentifier() or x in ("⊕", "↔", "⟲", "∇", "μ", "π", "⇒") else json.dumps(x, ensure_ascii=False)
        return json.dumps(x, ensure_ascii=False)

    body = ", ".join(s(a) for a in args) if args else ""
    return f"{op}({body})"

def _capsule_to_photon_text(capsule: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a validated capsule (supports glyph_stream or glyphs) to PhotonLang text.
    """
    items = capsule.get("glyph_stream") or capsule.get("glyphs") or []
    lines: List[str] = []
    for item in items:
        if isinstance(item, dict):
            if "operator" in item or "symbol" in item:
                lines.append(_glyph_to_photon_line(item))
            elif "expr" in item and isinstance(item["expr"], str):
                lines.append(item["expr"])
            else:
                lines.append(json.dumps(item, ensure_ascii=False))
        elif isinstance(item, str):
            lines.append(item)
        else:
            lines.append(json.dumps(item, ensure_ascii=False))
    return {
        "photon": "\n".join(lines),
        "count": len(lines),
        "name": capsule.get("name"),
        "engine": capsule.get("engine"),
    }
