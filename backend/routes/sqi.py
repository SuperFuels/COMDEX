from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from backend.modules.sqi.sqi_container_registry import sqi_registry
from backend.modules.sqi.knowledge_relinker import relinker
from backend.modules.sqi.sqi_materializer import materialize_entry
from backend.modules.sqi.sqi_metadata_embedder import make_kg_payload, bake_hologram_meta
from backend.modules.dimensions.universal_container_system import ucs_runtime
from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors

router = APIRouter()

# --------- Models ---------
class AllocateBody(BaseModel):
    kind: str
    domain: str
    name: str
    meta: Optional[Dict[str, Any]] = None

class RelinkBody(BaseModel):
    fact_id: str
    projects: List[Dict[str, Any]]

class UpsertMetaBody(BaseModel):
    meta: Dict[str, Any]

# --------- Core (existing) ---------
@router.post("/sqi/allocate")
def sqi_allocate(body: AllocateBody):
    try:
        entry = sqi_registry.allocate(
            kind=body.kind, domain=body.domain, name=body.name, meta=body.meta
        )
        return {"status": "ok", "entry": entry}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/sqi/ghx/hover/{cid}")
def sqi_ghx_hover(cid: str):
    entry = sqi_registry.get(cid)
    if not entry:
        # Fallback: try to build from UCS container snapshot
        try:
            c = ucs_runtime.get_container(cid) if hasattr(ucs_runtime, "get_container") else None
        except Exception:
            c = None
        if not c:
            raise HTTPException(404, f"Unknown container: {cid}")
        # bake HOV and build a minimal entry shape for the payload helper
        c = bake_hologram_meta(dict(c))
        entry = {"id": cid, "meta": c.get("meta", {})}

    # collapsed preview only (expand=False); client can toggle collapse first
    node = make_kg_payload(entry, expand=False)
    return {"status": "ok", "node": node}

@router.get("/sqi/lookup/{domain}")
def sqi_lookup_domain(domain: str):
    try:
        return {"status": "ok", "containers": sqi_registry.lookup_by_domain(domain)}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/sqi/relink")
def sqi_relink(body: RelinkBody):
    try:
        patches = relinker.relink_projects_for_updated_fact(
            fact_id=body.fact_id, projects=body.projects
        )
        return {"status": "ok", "patches": patches}
    except Exception as e:
        raise HTTPException(400, str(e))

# --------- New: materialization & combined flow ---------
@router.post("/sqi/materialize/{cid}")
def sqi_materialize(cid: str):
    entry = sqi_registry.get(cid)
    if not entry:
        raise HTTPException(404, f"Unknown container: {cid}")
    try:
        container = materialize_entry(entry)

        # ✅ Attach normalized validation errors
        raw_errors = validate_logic_trees(container)
        errors = normalize_validation_errors(raw_errors)
        container["validation_errors"] = errors
        container["validation_errors_version"] = "v1"

        return {"status": "ok", "container": container}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/sqi/allocate+materialize")
def sqi_allocate_and_materialize(body: AllocateBody):
    try:
        entry = sqi_registry.allocate(
            kind=body.kind, domain=body.domain, name=body.name, meta=body.meta
        )
        container = materialize_entry(entry)

        # ✅ Attach normalized validation errors
        raw_errors = validate_logic_trees(container)
        errors = normalize_validation_errors(raw_errors)
        container["validation_errors"] = errors
        container["validation_errors_version"] = "v1"

        return {"status": "ok", "entry": entry, "container": container}
    except Exception as e:
        raise HTTPException(400, str(e))

# --------- New: search / inverse index (stub until full index lands) ---------
@router.get("/sqi/search")
def sqi_search(
    q: str = Query("", description="Free-text filter over id/domain/tags"),
    domain: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
):
    try:
        ids = (
            sqi_registry.lookup_by_domain(domain)
            if domain
            else list(sqi_registry.index.keys())
        )
        q_l = (q or "").lower()
        results = []
        for cid in ids:
            e = sqi_registry.get(cid) or {}
            meta = e.get("meta", {}) or {}
            tags = meta.get("tags", []) or []
            text = " ".join([cid, e.get("domain", ""), " ".join(tags)]).lower()
            if (not q_l or q_l in text) and (not tag or tag in tags):
                results.append({"id": cid, "meta": meta})
        return {"status": "ok", "results": results}
    except Exception as e:
        raise HTTPException(400, str(e))

# --------- New: KG payload preview (no external write here) ---------
@router.get("/sqi/kg-payload/{cid}")
def sqi_kg_payload(cid: str):
    entry = sqi_registry.get(cid)
    if not entry:
        raise HTTPException(404, f"Unknown container: {cid}")
    try:
        node = make_kg_payload(entry)
        return {"status": "ok", "node": node}
    except Exception as e:
        raise HTTPException(400, str(e))

# --------- UPDATED: CR8 routing using new registry API ----------------------
@router.get("/sqi/route")
def sqi_route(
    domain: str = Query(...),
    kind: str = Query("fact"),
    topic: Optional[str] = Query(None),
):
    """
    Pick a container for {domain, kind[, topic]} using the registry's CR8 scoring.
    """
    entry = sqi_registry.choose_for(domain=domain, kind=kind, topic=topic)
    # Optional: expose the pool for debugging
    try:
        cands = [e["id"] for e in sqi_registry._collect_candidates()]
    except Exception:
        cands = list(sqi_registry.index.keys())
    return {"status": "ok", "entry": entry, "candidates": cands}

@router.post("/sqi/route/weights")
def sqi_route_weights(payload: Dict[str, Any]):
    """
    Hot-tune CR8 scoring weights.
    Body example:
      {"weights":{"domain_match":0.7,"freshness":0.2,"size_penalty":0.0,"priority_hint":0.1}}
    """
    weights = (payload or {}).get("weights") or {}
    updated = sqi_registry.set_route_weights(**weights)
    return {"status": "ok", "weights": updated}

# --------- Optional: meta upsert helper (handy to bias routing) -------------
@router.post("/sqi/upsert-meta/{cid}")
def sqi_upsert_meta(cid: str, body: UpsertMetaBody):
    try:
        entry = sqi_registry.upsert_meta(cid, body.meta)
        return {"status": "ok", "entry": entry}
    except Exception as e:
        raise HTTPException(400, str(e))