# -*- coding: utf-8 -*-
# backend/routes/sqi_drift.py
from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
import json, os

from backend.modules.sqi.sqi_math_adapter import compute_drift
from backend.modules.sqi.kg_bridge import write_report_to_kg

router = APIRouter(prefix="/api/sqi/drift", tags=["SQI Drift"])

_LAST: Optional[Dict[str, Any]] = None

@router.post("/compute")
def compute(payload: Dict[str, Any]):
    """
    Body: { container_path?: str, container?: {...} }
    Returns DriftReport (as dict)
    """
    global _LAST
    container = payload.get("container")
    cpath = payload.get("container_path")

    if container is None and cpath:
        if not os.path.exists(cpath):
            raise HTTPException(404, f"Container not found: {cpath}")
        with open(cpath, "r", encoding="utf-8") as f:
            container = json.load(f)

    if container is None:
        raise HTTPException(400, "Provide container or container_path")

    rep = compute_drift(container)
    rep_dict = {
        "container_id": rep.container_id,
        "total_weight": rep.total_weight,
        "status": rep.status,
        "gaps": [g.__dict__ for g in rep.gaps],
        "meta": rep.meta,
    }
    _LAST = rep_dict
    return rep_dict

@router.post("/apply")
def apply(payload: Dict[str, Any]):
    """
    Compute drift and write to Knowledge Graph (if available).
    """
    rep = compute(payload.get("container") or _load(payload.get("container_path")))
    res = write_report_to_kg(rep)
    return {"report": {
        "container_id": rep.container_id,
        "total_weight": rep.total_weight,
        "status": rep.status,
        "gaps": [g.__dict__ for g in rep.gaps],
        "meta": rep.meta,
    }, "kg": res}

@router.get("/list")
def list_last():
    return _LAST or {"message": "no drift computed this session"}

def _load(path: Optional[str]) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        raise HTTPException(404, "container_path missing or not found")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)