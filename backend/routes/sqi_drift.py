# -*- coding: utf-8 -*-
# backend/routes/sqi_drift.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json, os

from backend.modules.sqi.sqi_math_adapter import compute_drift
from backend.modules.sqi.sqi_harmonics import suggest_harmonics

router = APIRouter(prefix="/api/sqi", tags=["SQI Drift"])

def _load_container_by_path(path: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/drift")
def get_drift(container_path: str = Query(..., description="Path to .dc.json container"),
              suggest: bool = Query(False, description="Include lemma suggestions")):
    try:
        container = _load_container_by_path(container_path)
    except FileNotFoundError:
        raise HTTPException(404, f"Container not found: {container_path}")
    rep = compute_drift(container)

    payload = {
        "container_id": rep.container_id,
        "total_weight": rep.total_weight,
        "status": rep.status,
        "gaps": [g.__dict__ for g in rep.gaps],
        "meta": rep.meta,
    }

    if suggest and payload["gaps"]:
        # attach suggestions per missing dependency
        for gap in payload["gaps"]:
            if gap.get("reason") == "missing_dependencies":
                sug_list = []
                for miss in gap.get("missing", []):
                    cands = suggest_harmonics(container, miss, top_k=3)
                    sug_list.append({
                        "missing": miss,
                        "candidates": [{"name": n, "score": s} for (n, s) in cands]
                    })
                gap["suggestions"] = sug_list

    return payload