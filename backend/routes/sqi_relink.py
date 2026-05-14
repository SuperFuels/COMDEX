# -*- coding: utf-8 -*-
# backend/routes/sqi_relink.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors

router = APIRouter(prefix="/sqi", tags=["SQI-Relink"])

class RelinkReq(BaseModel):
    container_id: str

def _attach_validation(container: Dict[str, Any]) -> Dict[str, Any]:
    """Attach normalized validation errors if container looks valid."""
    try:
        raw_errors = validate_logic_trees(container)
        errors = normalize_validation_errors(raw_errors)
        container["validation_errors"] = errors
        container["validation_errors_version"] = "v1"
    except Exception as e:
        container["validation_errors"] = [{"code": "validation_failed", "message": str(e)}]
        container["validation_errors_version"] = "v1"
    return container

@router.post("/relink")
def relink(req: RelinkReq):
    kg = get_kg_writer()
    try:
        # If you have a real link-builder, call it here; otherwise do a light re-export
        out = kg.save_pack_for_container(req.container_id)  # helper we added earlier

        # Attach validation if out is container-like
        if isinstance(out, dict):
            out = _attach_validation(out)

        return {
            "status": "ok",
            "container_id": req.container_id,
            "pack": out,
            "validation_errors": out.get("validation_errors") if isinstance(out, dict) else None,
        }
    except Exception as e:
        raise HTTPException(500, f"Relink failed: {e}")