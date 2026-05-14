# backend/api/aion/prompt_api.py
from fastapi import APIRouter, HTTPException, Request
from typing import Any, Dict
from datetime import datetime, timezone
from backend.events.ghx_bus import broadcast

router = APIRouter(tags=["AION Prompt"])

@router.post("/prompt")
async def run_prompt(req: Request) -> Dict[str, Any]:
    body = await req.json()
    cid  = (body.get("container_id") or "").strip()
    text = (body.get("prompt") or "").strip()
    if not cid or not text:
        raise HTTPException(400, "container_id and prompt required")

    # Simple slash-commands (v1)
    if text.startswith("/clear"):
        from backend.modules.dna_chain.dc_handler import load_dc_container, save_dc_container
        try:
            dc = load_dc_container(cid)
        except FileNotFoundError:
            dc = {"id": cid, "type": "container", "glyphs": [], "meta": {}}
        dc["glyphs"] = []
        dc.setdefault("meta", {})["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_dc_container(cid, dc)
        await broadcast(cid, {"type":"glyphs_updated","container_id":cid,"glyph_count":0})
        return {"ok": True, "action": "clear"}

    if text.startswith("/inject"):
        payload = text.removeprefix("/inject").strip() or "note"
        glyphs = [
            {"id": f"g-{int(datetime.now().timestamp()*1000)}", "symbol": "⊕", "text": payload}
        ]
        from backend.modules.dna_chain.dc_handler import load_dc_container, save_dc_container
        try:
            dc = load_dc_container(cid)
        except FileNotFoundError:
            dc = {"id": cid, "type": "container", "glyphs": [], "meta": {}}
        dc.setdefault("glyphs", []).extend(glyphs)
        dc.setdefault("meta", {})["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_dc_container(cid, dc)
        await broadcast(cid, {"type":"glyphs_updated","container_id":cid,"added":len(glyphs),"glyph_count":len(dc["glyphs"])})
        return {"ok": True, "action": "inject", "added": len(glyphs)}

    # Default: echo analysis event to GHX (UI log)
    await broadcast(cid, {"type":"analysis","container_id":cid,"text":text,"ts":datetime.now(timezone.utc).isoformat()})
    return {"ok": True, "action": "analyze"}