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

import json, re
from typing import Dict, Any, List, Optional
OP_TOKENS = {"⊕", "↔", "⟲", "∇", "μ", "π", "⇒"}
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
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _text_to_jsonl_for_bridge(text: str) -> str:
    """
    Parse PhotonLang-ish lines into JSONL so the bridge always receives dicts.
    Supports:
      - emit "hello"   -> {"operator":"emit","args":["hello"]}
      - ⊕ (and core op tokens) -> {"operator":"⊕"}
      - anything else  -> {"expr":"<line>"}
    """
    OP_TOKENS = {"⊕", "↔", "⟲", "∇", "μ", "π", "⇒"}
    out: List[str] = []
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        m = re.match(r'^emit\s+["\'](.+?)["\']\s*$', s)
        if m:
            out.append(json.dumps({"operator": "emit", "args": [m.group(1)]}, ensure_ascii=False))
        elif s in OP_TOKENS:
            out.append(json.dumps({"operator": s}, ensure_ascii=False))
        else:
            out.append(json.dumps({"expr": s}, ensure_ascii=False))
    return "\n".join(out)

def _glyph_to_photon_line(g: Dict[str, Any]) -> str:
    """Simple readable formatter for a glyph item → PhotonLang-like syntax."""
    op = g.get("operator") or g.get("symbol") or "⊕"
    args = g.get("args") or []

    def s(x: Any) -> str:
        if isinstance(x, str):
            return x if x.isidentifier() or x in ("⊕", "↔", "⟲", "∇", "μ", "π", "⇒") else json.dumps(x, ensure_ascii=False)
        return json.dumps(x, ensure_ascii=False)

    body = ", ".join(s(a) for a in args) if args else ""
    return f"{op}({body})"

def _capsule_to_photon_text(capsule: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a capsule (glyph_stream|glyphs) → PhotonLang text (pretty)."""
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

def _capsule_to_jsonl_for_bridge(cap: Dict[str, Any]) -> str:
    """
    Convert capsule {glyphs|glyph_stream:[...]} → JSONL.
    Strings that are operator tokens become {"operator": "<op>"},
    other strings become {"expr": "<text>"}.
    Dict items are passed through as-is.
    """
    OP_TOKENS = {"⊕", "↔", "⟲", "∇", "μ", "π", "⇒"}
    seq = cap.get("glyph_stream") or cap.get("glyphs") or []
    out: List[str] = []
    for item in seq:
        if isinstance(item, dict):
            out.append(json.dumps(item, ensure_ascii=False))
        elif isinstance(item, str):
            if item in OP_TOKENS:
                out.append(json.dumps({"operator": item}, ensure_ascii=False))
            else:
                out.append(json.dumps({"expr": item}, ensure_ascii=False))
        else:
            out.append(json.dumps({"expr": item}, ensure_ascii=False))
    return "\n".join(out)

# ─────────────────────────────────────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────────────────────────────────────

class TranslateLineRequest(BaseModel):
    line: str

class CompileFileRequest(BaseModel):
    path: str

class ReverseRequest(BaseModel):
    glyphs: Optional[List[Any]] = None
    glyph_stream: Optional[List[Any]] = None
    capsule: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

class ReverseResponse(BaseModel):
    status: str = "ok"
    photon: str
    count: int
    name: Optional[str] = None
    engine: Optional[str] = None

# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/translate_line")
async def translate_line(req: TranslateLineRequest):
    try:
        result = translator.translate_line(req.line)
        return {"input": req.line, "translated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/translate_block")
async def translate_block(request: Request):
    data = await request.json()
    source = data.get("source", "")
    if not source.strip():
        return {"translated": ""}

    lines = source.splitlines()
    translated_lines: List[str] = []
    for line in lines:
        try:
            if line.strip():
                out = translator.translate_line(line)
                translated_lines.append(
                    out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
                )
            else:
                translated_lines.append("")
        except Exception as e:
            translated_lines.append(f"# ⚠️ Error: {e}")

    return {"translated": "\n".join(translated_lines)}

print("🛰️ [Photon API] Router active -> /api/photon/execute_raw")

@router.post("/execute_raw")
async def execute_raw(payload: Dict[str, Any]):
    """
    Accepts:
      - payload["source"] as PhotonLang text (string), or
      - payload["source"] as a capsule dict {glyphs|glyph_stream:[...]}
    We convert BOTH forms to JSONL (one JSON dict per line) so the bridge
    never receives bare strings.
    """
    if bridge is None:
        raise HTTPException(status_code=500, detail="PhotonSymaticsBridge unavailable.")

    try:
        source = payload.get("source")
        if source is None:
            raise HTTPException(status_code=400, detail="Missing 'source' field")

        # A) Raw PhotonLang-ish text → JSONL
        if isinstance(source, str):
            photon_text = _text_to_jsonl_for_bridge(source)

        # B) Capsule dict → normalize → JSONL
        elif isinstance(source, dict):
            cap = dict(source)
            if "glyphs" not in cap and "glyph_stream" in cap:
                cap["glyphs"] = cap["glyph_stream"]
            if "glyph_stream" not in cap and "glyphs" in cap:
                cap["glyph_stream"] = cap["glyphs"]
            if ("glyphs" not in cap) and ("glyph_stream" not in cap):
                raise HTTPException(status_code=400, detail="capsule must contain glyphs or glyph_stream")

            try:
                validate_photon_capsule(cap)
            except Exception:
                pass  # best-effort even if strict validation fails

            photon_text = _capsule_to_jsonl_for_bridge(cap)

        else:
            raise HTTPException(status_code=400, detail="Invalid 'source' type (must be str or capsule dict)")

        results = await bridge.execute_raw(photon_text)
        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"execute_raw failed: {e}")

@router.post("/compile_file")
async def compile_file(req: CompileFileRequest):
    try:
        compiled = translator.compile_file(req.path)
        return {"status": "ok", "compiled": compiled}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {req.path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/translate_reverse", response_model=ReverseResponse)
async def translate_reverse(body: ReverseRequest):
    """
    Accepts:
      - { glyphs: [...]} or { glyph_stream: [...] }
      - { capsule: { glyphs|glyph_stream: [...], ... } }
    Returns PhotonLang text + count.
    """
    if body.capsule:
        capsule = dict(body.capsule)
    else:
        seq = body.glyphs or body.glyph_stream
        if not seq or not isinstance(seq, list):
            raise HTTPException(status_code=400, detail="Provide glyphs[], glyph_stream[], or capsule{}")
        capsule = {"glyphs": seq}

    try:
        if 'validate_photon_capsule' in globals() and callable(validate_photon_capsule):
            validate_photon_capsule(capsule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid capsule: {e}")

    out = _capsule_to_photon_text(capsule)
    return ReverseResponse(
        status="ok",
        photon=out["photon"],
        count=out["count"],
        name=out.get("name"),
        engine=out.get("engine"),
    )

@router.post("/translate_reverse_file", response_model=ReverseResponse)
async def translate_reverse_file(file: UploadFile = File(...)):
    """
    Accepts a JSON file containing a capsule (supports glyphs or glyph_stream)
    and returns PhotonLang text (one line per glyph item).
    """
    try:
        raw = await file.read()
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="File must contain a JSON object (capsule)")

        try:
            validate_photon_capsule(data)
        except Exception:
            pass  # best-effort

        out = _capsule_to_photon_text(data)
        return ReverseResponse(
            status="ok",
            photon=out["photon"],
            count=out["count"],
            name=out.get("name"),
            engine=out.get("engine"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")