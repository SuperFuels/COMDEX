# backend/api/aion/container_api.py
from fastapi import APIRouter, HTTPException, Request
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from backend.events.ghx_bus import broadcast  # 🟢 notify frontends on updates

router = APIRouter(tags=["AION Containers"])

# --------------------------- helpers ---------------------------

def _normalize_id(raw: str) -> str:
    v = (raw or "").strip()
    return v[:-3] if v.endswith(".tp") else v

def _ensure_dc_shape(dc: Dict[str, Any], cid: str) -> Dict[str, Any]:
    dc.setdefault("id", cid)
    dc.setdefault("type", dc.get("type") or "container")
    dc.setdefault("glyphs", dc.get("glyphs") or [])
    dc.setdefault("meta", dc.get("meta") or {})
    return dc

# --------------------------- routes ----------------------------

@router.get("/containers")
def list_containers() -> Dict[str, Any]:
    """
    List known containers. Prefer on-disk list, fallback to STATE registry.
    """
    # try file-backed list
    try:
        from backend.modules.dna_chain.dc_handler import list_available_containers
        containers = list_available_containers()  # [{id,...}, ...]
        return {"containers": containers}
    except Exception:
        pass

    # fallback: STATE registry
    try:
        from backend.modules.consciousness.state_manager import STATE
        return {"containers": STATE.list_containers_with_status()}
    except Exception as e:
        raise HTTPException(500, f"Failed to list containers: {e}")

@router.get("/container/{container_id}")
def get_container(container_id: str) -> Dict[str, Any]:
    """
    Minimal decrypted .dc view: { id, type, glyphs, meta }
    Try filesystem .dc first, then STATE registry.
    """
    cid = _normalize_id(container_id)

    # 1) on-disk .dc
    try:
        from backend.modules.dna_chain.dc_handler import load_dc_container
        dc = load_dc_container(cid)
        return _ensure_dc_shape(dc, cid)
    except FileNotFoundError:
        pass
    except Exception as e:
        raise HTTPException(500, f"Load failed: {e}")

    # 2) STATE registry fallback
    try:
        from backend.modules.consciousness.state_manager import STATE
        containers = STATE.list_containers_with_status()
    except Exception as e:
        raise HTTPException(500, f"STATE unavailable: {e}")

    rec = next((c for c in containers if c.get("id") == cid or c.get("name") == cid), None)
    if not rec:
        raise HTTPException(404, f"Container not found: {cid}")

    dc = (rec.get("dc") or rec.get("meta", {}).get("dc")) or {
        "id": rec.get("id") or cid,
        "type": rec.get("kind") or "container",
        "glyphs": rec.get("glyphs") or [],
        "meta": {k: v for k, v in rec.items() if k not in {"dc", "glyphs"} and v is not None},
    }
    return _ensure_dc_shape(dc, cid)

@router.post("/container/save/{container_id}")
async def save_container(container_id: str, req: Request) -> Dict[str, Any]:
    cid = _normalize_id(container_id)
    data = await req.json()
    try:
        from backend.modules.dna_chain.dc_handler import save_dc_container
        save_dc_container(cid, data)
    except Exception as e:
        raise HTTPException(500, f"Save failed: {e}")

    glyph_count = len((data or {}).get("glyphs") or [])

    # best-effort memory log (optional)
    try:
        from backend.modules.hexcore.memory_engine import MEMORY
        MEMORY.store({
            "role": "system",
            "label": "container_saved",
            "content": f"saved {cid} ({glyph_count} glyphs)"
        })
    except Exception:
        pass

    # notify clients so the UI auto-refreshes
    try:
        await broadcast(cid, {
            "type": "glyphs_updated",
            "container_id": cid,
            "glyph_count": glyph_count,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    return {"status": "ok", "id": cid}

@router.post("/container/inject-glyphs/{container_id}")
async def inject_glyphs(container_id: str, req: Request) -> Dict[str, Any]:
    """
    Append glyphs to the container's .dc.
    Body: { "glyphs": [ {id?, symbol?, text?, meta?}, ... ], "source"?: str }
    """
    cid = _normalize_id(container_id)
    body = await req.json()
    glyphs: List[dict] = list(body.get("glyphs") or [])
    if not glyphs:
        raise HTTPException(400, "No glyphs provided.")

    # load or create
    try:
        from backend.modules.dna_chain.dc_handler import load_dc_container, save_dc_container
        try:
            dc = load_dc_container(cid)
        except FileNotFoundError:
            dc = {"id": cid, "type": "container", "glyphs": [], "meta": {}}
    except Exception as e:
        raise HTTPException(500, f"Load failed: {e}")

    _ensure_dc_shape(dc, cid)
    dc["glyphs"].extend(glyphs)

    # update stamp
    dc["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()

    try:
        save_dc_container(cid, dc)
    except Exception as e:
        raise HTTPException(500, f"Save failed: {e}")

    # 🟢 notify GHX listeners so frontends can live-refresh
    try:
        await broadcast(cid, {
            "type": "glyphs_updated",
            "container_id": cid,
            "added": len(glyphs),
            "glyph_count": len(dc["glyphs"]),
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        # non-fatal if bus is not available
        pass

    # optional memory note
    try:
        from backend.modules.hexcore.memory_engine import MEMORY
        MEMORY.store({"role": "system", "label": "glyph_injection",
                      "content": f"Injected {len(glyphs)} glyphs into {cid}"})
    except Exception:
        pass

    return {"status": "ok", "id": cid, "glyph_count": len(dc["glyphs"])}

@router.post("/container/teleport")
async def teleport_container(req: Request) -> Dict[str, Any]:
    """
    Body: { "source": str, "destination": str, "reason"?: str }
    """
    body = await req.json()
    source: str = body.get("source")
    dest: str = body.get("destination")
    reason: Optional[str] = body.get("reason") or "api_call"
    if not source or not dest:
        raise HTTPException(400, "source and destination required")

    try:
        from backend.modules.dna_chain.teleport import teleport
        teleport(source, dest, reason=reason)
    except Exception as e:
        raise HTTPException(500, f"Teleport failed: {e}")

    # optional memory note
    try:
        from backend.modules.hexcore.memory_engine import MEMORY
        MEMORY.store({"role": "system", "label": "teleport",
                      "content": f"teleport {source} -> {dest} ({reason})"})
    except Exception:
        pass

    return {"status": "ok", "from": source, "to": dest, "reason": reason}