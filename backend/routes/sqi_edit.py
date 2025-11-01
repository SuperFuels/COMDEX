from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.modules.dimensions.universal_container_system import ucs_runtime
from backend.modules.sqi.sqi_metadata_embedder import bake_hologram_meta  # keep HOV flags consistent
from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors

router = APIRouter(prefix="/sqi", tags=["SQI Edit"])

# ---------- Models ----------
class NodeBody(BaseModel):
    container_id: str
    node_id: str
    label: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class LinkBody(BaseModel):
    container_id: str
    source: str
    target: str
    relation: str = "RELATED"
    meta: Optional[Dict[str, Any]] = None

# ---------- Helpers ----------
def _get_or_make_container(cid: str) -> Dict[str, Any]:
    # Try to fetch; if missing, error (we expect you to /sqi/allocate+materialize first)
    c = None
    if hasattr(ucs_runtime, "get_container"):
        c = ucs_runtime.get_container(cid)
    elif hasattr(ucs_runtime, "index"):
        c = getattr(ucs_runtime, "index", {}).get(cid)

    if not c:
        raise HTTPException(404, f"Unknown container: {cid}")

    # ensure glyph_grid array exists + HOV baked
    c.setdefault("glyph_grid", [])
    c = bake_hologram_meta(c)
    return c

def _save_container(cid: str, c: Dict[str, Any]) -> Dict[str, Any]:
    # idempotent register/merge back into UCS
    return ucs_runtime.register_container(cid, c)

def _attach_validation(container: Dict[str, Any]) -> Dict[str, Any]:
    """Attach normalized validation errors consistently."""
    try:
        raw_errors = validate_logic_trees(container)
        errors = normalize_validation_errors(raw_errors)
        container["validation_errors"] = errors
        container["validation_errors_version"] = "v1"
    except Exception as e:
        # Don't break API on validation failure; just log in container
        container["validation_errors"] = [{"code": "validation_failed", "message": str(e)}]
        container["validation_errors_version"] = "v1"
    return container

# ---------- Endpoints ----------
@router.post("/add-node")
def add_node(body: NodeBody):
    c = _get_or_make_container(body.container_id)

    # de-dupe: remove any existing kg_node with same id
    gg = [
        g
        for g in c["glyph_grid"]
        if not (g.get("type") == "kg_node" and g.get("metadata", {}).get("id") == body.node_id)
    ]

    node = {
        "type": "kg_node",
        "metadata": {
            "id": body.node_id,
            "label": body.label or body.node_id,
            **(body.meta or {}),
        },
    }
    gg.append(node)
    c["glyph_grid"] = gg

    saved = _save_container(body.container_id, c)
    saved = _attach_validation(saved)

    return {
        "status": "ok",
        "container_id": body.container_id,
        "node": node,
        "count": len(saved.get("glyph_grid", [])),
        "validation_errors": saved.get("validation_errors"),
    }

@router.post("/add-link")
def add_link(body: LinkBody):
    c = _get_or_make_container(body.container_id)

    link = {
        "type": "kg_edge",
        "metadata": {
            "from": body.source,
            "to": body.target,
            "relation": body.relation,
            **(body.meta or {}),
        },
    }
    c["glyph_grid"].append(link)

    saved = _save_container(body.container_id, c)
    saved = _attach_validation(saved)

    return {
        "status": "ok",
        "container_id": body.container_id,
        "link": link,
        "count": len(saved.get("glyph_grid", [])),
        "validation_errors": saved.get("validation_errors"),
    }

# ---------- Convenience seeder ----------
@router.post("/seed/maxwell")
def seed_maxwell(container_id: str = "maxwell_core"):
    """
    Seeds 4 Maxwell nodes + a couple of illustrative edges.
    """
    # nodes
    nodes = [
        {"node_id": "E", "label": "Electric Field E", "meta": {"domain": "physics.em", "tags": ["field", "maxwell"]}},
        {"node_id": "B", "label": "Magnetic Field B", "meta": {"domain": "physics.em", "tags": ["field", "maxwell"]}},
        {"node_id": "ρ", "label": "Charge Density ρ", "meta": {"domain": "physics.em", "tags": ["source"]}},
        {"node_id": "J", "label": "Current Density J", "meta": {"domain": "physics.em", "tags": ["source"]}},
    ]
    for n in nodes:
        add_node(NodeBody(container_id=container_id, **n))

    # edges (illustrative, not full PDEs)
    links = [
        {"source": "E", "target": "ρ", "relation": "div_E = ρ/ε0"},
        {"source": "B", "target": "J", "relation": "curl_B = μ0 J + μ0 ε0 ∂E/∂t"},
    ]
    for l in links:
        add_link(LinkBody(container_id=container_id, **l))

    return {"status": "ok", "seeded": len(nodes) + len(links), "container_id": container_id}