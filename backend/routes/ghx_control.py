# backend/routes/ghx_control.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any

from backend.modules.sqi.sqi_container_registry import sqi_registry
from backend.modules.sqi.sqi_metadata_embedder import make_kg_payload, bake_hologram_meta
from backend.modules.dimensions.universal_container_system import ucs_runtime

router = APIRouter()

def _ensure_in_ucs(cid: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort: make sure a UCS container exists/updated with the baked GHX meta."""
    # Rebuild a minimal container snapshot and re-register to UCS
    container = {
        "id": cid,
        "type": "container",
        "kind": entry.get("kind"),
        "domain": entry.get("domain"),
        "meta": dict(entry.get("meta") or {}),
        "atoms": {},
        "wormholes": [],
        "nodes": [],
        "glyphs": [],
    }
    container = bake_hologram_meta(container)
    try:
        ucs_runtime.register_container(cid, container)
    except Exception:
        # non-fatal: UCS not available in some dev contexts
        pass
    return container

@router.get("/sqi/ghx/hover/{cid}")
def get_hover_node(cid: str):
    """Return a KG-ready node (collapsed view) for hover previews."""
    entry = sqi_registry.get(cid)
    if not entry:
        raise HTTPException(404, f"Unknown container: {cid}")
    node = make_kg_payload({"id": cid, "meta": entry.get("meta", {})}, expand=False)
    return {"status": "ok", "node": node}

@router.post("/sqi/ghx/collapse/{cid}")
def set_ghx_collapse(
    cid: str,
    collapsed: bool = Query(..., description="true or false"),
    density: Optional[str] = Query(None, description="optional density hint, e.g., 'auto'|'low'|'high'"),
    snapshot_rate: Optional[float] = Query(None, description="optional time-dilation snapshot rate"),
    mode: Optional[str] = Query(None, description="optional time-dilation mode: normal|compressed|frozen"),
):
    """
    Toggle GHX collapsed flag (HOV3) and optional density/time-dilation hints (HOV4).
    """
    entry = sqi_registry.get(cid)
    if not entry:
        raise HTTPException(404, f"Unknown container: {cid}")

    # Patch registry meta
    ghx = dict((entry.get("meta") or {}).get("ghx") or {})
    ghx["collapsed"] = bool(collapsed)
    if density is not None:
        ghx["density"] = density

    meta_patch: Dict[str, Any] = {"ghx": ghx}
    # Optional time-dilation hints
    td = dict((entry.get("meta") or {}).get("time_dilation") or {})
    if mode is not None:
        td["mode"] = mode
    if snapshot_rate is not None:
        td["snapshot_rate"] = float(snapshot_rate)
    if td:
        meta_patch["time_dilation"] = td

    updated = sqi_registry.upsert_meta(cid, meta_patch)

    # Mirror into UCS (so GHX export path sees it)
    _ensure_in_ucs(cid, {**entry, "meta": updated.get("meta", {})})

    # Return the KG node preview reflecting the new collapsed state
    node = make_kg_payload({"id": cid, "meta": updated.get("meta", {})}, expand=not collapsed)
    return {"status": "ok", "collapsed": collapsed, "node": node}