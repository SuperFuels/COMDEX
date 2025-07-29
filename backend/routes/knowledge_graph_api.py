# File: backend/routes/knowledge_graph_api.py

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from backend.modules.knowledge_graph.knowledge_index import knowledge_index
from backend.modules.knowledge_graph.indexes.tag_index import (
    query_by_tag, query_multi_tags, list_tags
)  # ✅ NEW: Tag index utilities
from backend.modules.glyphnet.glyphnet_ws import broadcast_anchor_update
from backend.modules.state.container_loader import load_container_by_id  # ✅ For recursive traversal
from backend.modules.soul.soul_law_validator import soul_law_validator  # ✅ For A3d SoulLaw

router = APIRouter(prefix="/api/kg", tags=["Knowledge Graph"])

# ✅ In-memory anchor registry
ANCHOR_REGISTRY: Dict[str, Dict[str, Any]] = {}

class AnchorRequest(BaseModel):
    glyph_id: str
    env_obj_id: str
    type: str
    coord: Dict[str, float]
    avatar_state: Optional[Dict[str, Any]] = None  # ✅ Added for SoulLaw validation

class QueryRequest(BaseModel):
    glyph: Optional[str] = None
    tags: Optional[List[str]] = None
    reasoning: Optional[str] = None
    container_id: Optional[str] = None
    include_entangled: bool = True
    tick_range: Optional[List[int]] = None  # ✅ For A3c tick filtering
    avatar_state: Optional[Dict[str, Any]] = None  # ✅ For SoulLaw identity checks

# ────────────────────────────────────────────────
# ✅ A4c: Tag index API
# ────────────────────────────────────────────────
@router.get("/tags")
async def get_tags(avatar_state: Optional[Dict[str, Any]] = Query(None)):
    """
    List all tags in the Knowledge Graph.
    Secured by SoulLaw validation.
    """
    if not soul_law_validator.validate_avatar(avatar_state):
        raise HTTPException(status_code=403, detail="SoulLaw validation failed: unauthorized identity")
    return {"tags": list_tags()}

@router.get("/tags/{tag}")
async def query_by_single_tag(tag: str, avatar_state: Optional[Dict[str, Any]] = Query(None)):
    """
    Query glyphs by a single tag.
    """
    if not soul_law_validator.validate_avatar(avatar_state):
        raise HTTPException(status_code=403, detail="SoulLaw validation failed: unauthorized identity")
    return {"tag": tag, "results": query_by_tag(tag)}

@router.post("/tags/multi")
async def query_by_multiple_tags(
    tags: List[str],
    avatar_state: Optional[Dict[str, Any]] = None
):
    """
    Query glyphs matching any of the provided tags.
    """
    if not soul_law_validator.validate_avatar(avatar_state):
        raise HTTPException(status_code=403, detail="SoulLaw validation failed: unauthorized identity")
    return {"tags": tags, "results": query_multi_tags(tags)}

# ────────────────────────────────────────────────
# Existing endpoints remain unchanged below...
# (anchors, query_knowledge_graph, traverse_entangled_containers, is_within_tick_range)
# ────────────────────────────────────────────────

@router.get("/anchors")
async def get_anchors(
    glyph_id: Optional[str] = Query(None, description="Filter by glyph ID"),
    avatar_state: Optional[Dict[str, Any]] = Query(None)
):
    if not soul_law_validator.validate_avatar(avatar_state):
        raise HTTPException(status_code=403, detail="SoulLaw validation failed: unauthorized identity")
    if glyph_id:
        anchor = ANCHOR_REGISTRY.get(glyph_id)
        if not anchor:
            raise HTTPException(status_code=404, detail="Anchor not found for glyph_id")
        return {"glyph_id": glyph_id, "anchor": anchor}
    return {"anchors": ANCHOR_REGISTRY}

@router.post("/anchors")
async def set_anchor(req: AnchorRequest):
    if not soul_law_validator.validate_avatar(req.avatar_state):
        raise HTTPException(status_code=403, detail="SoulLaw validation failed: unauthorized identity")
    anchor_data = {
        "env_obj_id": req.env_obj_id,
        "type": req.type,
        "coord": req.coord,
    }
    ANCHOR_REGISTRY[req.glyph_id] = anchor_data
    await broadcast_anchor_update(req.glyph_id, anchor_data)
    knowledge_index.add_entry(
        glyph=req.glyph_id,
        meaning=f"Anchor linked to {req.type} ({req.env_obj_id})",
        tags=["anchor", "environment"],
        source="anchor_update",
        container_id=req.env_obj_id,
        confidence=1.0,
        plugin="environment_anchor"
    )
    return {"status": "ok", "glyph_id": req.glyph_id, "anchor": anchor_data}

@router.post("/query")
async def query_knowledge_graph(req: QueryRequest):
    if not soul_law_validator.validate_avatar(req.avatar_state):
        raise HTTPException(status_code=403, detail="SoulLaw validation failed: unauthorized identity")
    results = []
    local_entries = knowledge_index.entries
    for e in local_entries:
        if req.glyph and e["glyph"] != req.glyph:
            continue
        if req.tags and not any(tag in e.get("tags", []) for tag in req.tags):
            continue
        if req.reasoning and req.reasoning.lower() not in e.get("meaning", "").lower():
            continue
        results.append({**e, "source": "local"})
    if req.include_entangled and req.container_id:
        nested_results = await traverse_entangled_containers(req.container_id, req)
        results.extend(nested_results)
    if req.tick_range:
        start, end = req.tick_range
        results = [r for r in results if "timestamp" in r and is_within_tick_range(r["timestamp"], start, end)]
    return {"query": req.dict(), "count": len(results), "results": results}

async def traverse_entangled_containers(container_id: str, req: QueryRequest) -> List[Dict[str, Any]]:
    visited = set()
    results = []
    async def recurse(cid: str):
        if cid in visited:
            return
        visited.add(cid)
        container = await load_container_by_id(cid)
        if not container:
            return
        for glyph in container.get("glyph_grid", []):
            if req.glyph and glyph.get("content") != req.glyph:
                continue
            if req.tags and not any(tag in glyph.get("metadata", {}).get("tags", []) for tag in req.tags):
                continue
            if req.reasoning and req.reasoning.lower() not in glyph.get("metadata", {}).get("reasoning", "").lower():
                continue
            results.append({**glyph, "source": f"container:{cid}"})
        for ent in container.get("entangled_containers", []):
            await recurse(ent)
    await recurse(container_id)
    return results

def is_within_tick_range(timestamp: str, start: int, end: int) -> bool:
    try:
        tick = abs(hash(timestamp)) % 10000
        return start <= tick <= end
    except Exception:
        return False