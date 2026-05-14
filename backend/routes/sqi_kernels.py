# -*- coding: utf-8 -*-
# backend/routes/sqi_kernels.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from backend.modules.physics.physics_kernel_ingest import ingest_physics_fact

router = APIRouter(prefix="/sqi/kernel", tags=["SQI-Kernels"])

class PhysicsIngest(BaseModel):
    name: str
    data: Dict[str, Any] = Field(default_factory=dict)
    # ✅ Optional explicit target container (overrides registry routing)
    container_id: Optional[str] = None

@router.post("/physics/ingest")
def physics_ingest(req: PhysicsIngest):
    try:
        # Prefer explicit container_id; fall back to data.container_id if present
        target_cid = req.container_id or req.data.get("container_id")
        res = ingest_physics_fact(req.name, req.data, container_id=target_cid)

        # normalize a friendly response shape
        return {"status": "ok", **(res if isinstance(res, dict) else {"result": res})}
    except HTTPException:
        raise
    except Exception as e:
        # surface errors as JSON instead of HTML 500
        raise HTTPException(status_code=500, detail=str(e))