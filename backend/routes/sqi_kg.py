# -*- coding: utf-8 -*-
# backend/routes/sqi_kg.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json, os

from backend.modules.sqi.sqi_math_adapter import compute_drift
from backend.modules.sqi.sqi_kg_bridge import write_drift_report_to_kg
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