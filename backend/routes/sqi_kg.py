# -*- coding: utf-8 -*-
# backend/routes/sqi_kg.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json, os

from backend.modules.sqi.sqi_math_adapter import compute_drift
from backend.modules.sqi.kg_bridge import write_report_to_kg as write_drift_report_to_kg
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

router = APIRouter(prefix="/api/sqi/kg", tags=["SQI-KG"])

class DriftToKGReq(BaseModel):
    container_path: str
    suggest: bool = False

@router.post("/drift/push")
def push_drift(req: DriftToKGReq):
    if not os.path.exists(req.container_path):
        raise HTTPException(404, "container_path not found")
    with open(req.container_path, "r", encoding="utf-8") as f:
        container = json.load(f)
    rep = compute_drift(container)
    # serialize report dict (like compute_drift.py did)
    report = {
        "container_id": rep.container_id,
        "total_weight": rep.total_weight,
        "status": rep.status,
        "gaps": [g.__dict__ for g in rep.gaps],
        "meta": rep.meta,
    }
    out = write_drift_report_to_kg(report, req.container_path)
    return {"status": "ok", **out, "report": report}

@router.get("/nodes")
def list_nodes(kind: str | None = None, limit: int = 50):
    kg = KnowledgeGraphWriter()
    return {"nodes": kg.list_nodes(kind=kind, limit=limit)}

@router.get("/nodes/{node_id}")
def get_node(node_id: str):
    kg = KnowledgeGraphWriter()
    node = kg.read_node(node_id)
    if not node:
        raise HTTPException(404, "node not found")
    return node


# --- UCS container inspection & export ---

from pathlib import Path
from backend.modules.dimensions.universal_container_system import ucs_runtime

def _get_container(cid: str) -> dict:
    if hasattr(ucs_runtime, "get_container"):
        c = ucs_runtime.get_container(cid)
        if c:
            return c
    if hasattr(ucs_runtime, "index") and cid in getattr(ucs_runtime, "index"):
        return ucs_runtime.index[cid]
    if hasattr(ucs_runtime, "registry") and cid in getattr(ucs_runtime, "registry"):
        return ucs_runtime.registry[cid]
    return {}

@router.get("/ucs/list")
def list_ucs_containers():
    ids = []
    if hasattr(ucs_runtime, "list_containers"):
        ids = ucs_runtime.list_containers() or []
    elif hasattr(ucs_runtime, "index"):
        ids = list(getattr(ucs_runtime, "index", {}).keys())
    elif hasattr(ucs_runtime, "registry"):
        ids = list(getattr(ucs_runtime, "registry", {}).keys())
    return {"status": "ok", "ids": ids}

@router.post("/export-pack/{cid}")
def export_pack(cid: str, filename: str | None = None):
    c = _get_container(cid)
    if not c:
        raise HTTPException(404, f"Container not found in UCS: {cid}")

    out = filename or f"{cid}.kg.json"
    out_path = Path("backend/modules/dimensions/containers/kg_exports") / out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    w = KnowledgeGraphWriter()
    saved = w.export_pack(c, out_path)
    return {"status": "ok", "file": saved}

# -- Debug: compute on-disk path for a container and whether it exists
@router.get("/container-path/{cid}")
def get_container_path(cid: str):
    kg = KnowledgeGraphWriter()
    path = kg._container_path_for(cid)  # implementation detail but handy
    exists = False
    try:
        exists = os.path.exists(path)
    except Exception:
        pass
    return {"status": "ok", "cid": cid, "path": path, "exists": exists}

# -- Load from disk into UCS by cid (uses KG writer's path helper)
@router.post("/load-into-ucs/{cid}")
def load_into_ucs(cid: str):
    kg = KnowledgeGraphWriter()
    path = kg._container_path_for(cid)
    if not os.path.exists(path):
        raise HTTPException(404, f"Container file not found: {path}")
    try:
        from backend.modules.dimensions.universal_container_system import ucs_runtime
        ucs_runtime.load_container_from_file(path)
        return {"status": "ok", "cid": cid, "path": path, "loaded": True}
    except Exception as e:
        raise HTTPException(500, f"Load failed: {e}")