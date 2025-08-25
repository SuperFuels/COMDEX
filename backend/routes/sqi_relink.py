# -*- coding: utf-8 -*-
# backend/routes/sqi_relink.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

router = APIRouter(prefix="/sqi", tags=["SQI-Relink"])

class RelinkReq(BaseModel):
    container_id: str

@router.post("/relink")
def relink(req: RelinkReq):
    kg = get_kg_writer()
    try:
        # If you have a real link-builder, call it here; otherwise do a light re-export
        out = kg.save_pack_for_container(req.container_id)  # helper we added earlier
        return {"status": "ok", "container_id": req.container_id, "pack": out}
    except Exception as e:
        raise HTTPException(500, f"Relink failed: {e}")