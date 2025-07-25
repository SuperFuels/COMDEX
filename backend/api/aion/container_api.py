from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import asyncio

from backend.modules.consciousness.state_manager import STATE
from backend.modules.dna_chain.dc_handler import (
    list_available_containers,
    load_dc_container,
    save_dc_container,
    inject_glyphs_into_container,
)
from backend.modules.hexcore.memory_engine import MEMORY

router = APIRouter()

class GlyphInjectRequest(BaseModel):
    glyphs: List[dict]  # [{ "symbol": str, "meta": Optional[dict] }]
    source: Optional[str] = "manual"

class TeleportRequest(BaseModel):
    source: str
    destination: str
    reason: Optional[str] = None

@router.get("/containers")
async def get_containers():
    try:
        containers = list_available_containers()
        return JSONResponse(content={"containers": containers})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list containers: {e}")

@router.get("/container/{container_id}")
async def get_container(container_id: str):
    try:
        container = load_dc_container(container_id)
        return JSONResponse(content=container)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading container: {e}")

@router.post("/container/save/{container_id}")
async def save_container(container_id: str, request: Request):
    try:
        data = await request.json()
        save_dc_container(container_id, data)
        MEMORY.store({
            "role": "system",
            "label": "container_saved",
            "content": f"Container '{container_id}' saved.",
        })
        return {"status": "success", "message": f"Container '{container_id}' saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save container: {e}")

@router.post("/container/inject-glyphs/{container_id}")
async def inject_glyphs(container_id: str, payload: GlyphInjectRequest):
    try:
        success = inject_glyphs_into_container(container_id, payload.glyphs, payload.source)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to inject glyphs.")
        MEMORY.store({
            "role": "system",
            "label": "glyph_injection",
            "content": f"Injected {len(payload.glyphs)} glyph(s) into container '{container_id}'."
        })
        return {"status": "success", "message": f"Injected {len(payload.glyphs)} glyph(s)."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Glyph injection error: {e}")

@router.post("/container/teleport")
async def teleport_container(request: TeleportRequest):
    try:
        # Use state manager to handle teleport (simulate)
        from backend.modules.dna_chain.teleport import teleport
        teleport(request.source, request.destination, reason=request.reason or "api_call")
        MEMORY.store({
            "role": "system",
            "label": "teleport",
            "content": f"Teleported from {request.source} to {request.destination} (reason: {request.reason})"
        })
        return {"status": "success", "message": f"Teleported from {request.source} to {request.destination}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teleport failed: {e}")