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
from backend.modules.dimensions.glyph_logic import get_entangled_links_for_universal_container_system

router = APIRouter()

class GlyphInjectRequest(BaseModel):
    glyphs: List[dict]  # [{ "symbol": str, "meta": Optional[dict] }]
    source: Optional[str] = "manual"

class TeleportRequest(BaseModel):
    source: str
    destination: str
    reason: Optional[str] = None


# 🔑 Permission Helper
def _apply_permissions(glyphs: List[dict], agent_id: str) -> List[dict]:
    """
    Apply permission tagging to glyphs based on requesting agent.
    """
    filtered = []
    for g in glyphs:
        meta = g.get("metadata", {})
        owner = meta.get("agent_id", "system")
        private = meta.get("private", False)

        if owner == agent_id or agent_id == "system":
            meta["permission"] = "editable"
            filtered.append(g)
        elif private:
            meta["permission"] = "hidden"
            continue
        else:
            meta["permission"] = "read-only"
            filtered.append(g)
        g["metadata"] = meta
    return filtered


@router.get("/containers")
async def get_containers():
    try:
        containers = list_available_containers()
        container_map = {c["id"]: c for c in containers}

        # Inject ↔ entangled container links
        for container in containers:
            try:
                entangled_ids = get_entangled_links_for_container(container["id"])
                container["connected"] = [eid for eid in entangled_ids if eid in container_map]
            except Exception:
                container["connected"] = []

        return JSONResponse(content={"containers": containers})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list containers: {e}")


@router.get("/container/{container_id}")
async def get_container(container_id: str, request: Request):
    try:
        agent_id = request.headers.get("X-Agent-ID", "anonymous")
        container = load_dc_container(container_id)

        # ✅ Apply permissions to glyphs in container
        if "glyph_grid" in container:
            container["glyph_grid"] = _apply_permissions(container["glyph_grid"], agent_id)

        return JSONResponse(content=container)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading container: {e}")


@router.post("/container/save/{container_id}")
async def save_container(container_id: str, request: Request):
    try:
        agent_id = request.headers.get("X-Agent-ID", "anonymous")
        data = await request.json()
        save_dc_container(container_id, data)

        MEMORY.store({
            "role": "system",
            "label": "container_saved",
            "content": f"Agent {agent_id} saved container '{container_id}'."
        })
        return {"status": "success", "message": f"Container '{container_id}' saved by {agent_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save container: {e}")


@router.post("/container/inject-glyphs/{container_id}")
async def inject_glyphs(container_id: str, payload: GlyphInjectRequest, request: Request):
    try:
        agent_id = request.headers.get("X-Agent-ID", "anonymous")
        # Tag injected glyphs with agent identity
        for g in payload.glyphs:
            g.setdefault("metadata", {})["agent_id"] = agent_id

        success = inject_glyphs_into_container(container_id, payload.glyphs, payload.source)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to inject glyphs.")

        MEMORY.store({
            "role": "system",
            "label": "glyph_injection",
            "content": f"Agent {agent_id} injected {len(payload.glyphs)} glyph(s) into container '{container_id}'."
        })
        return {"status": "success", "message": f"Injected {len(payload.glyphs)} glyph(s) by {agent_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Glyph injection error: {e}")


@router.post("/container/teleport")
async def teleport_container(request: TeleportRequest, http_req: Request):
    try:
        agent_id = http_req.headers.get("X-Agent-ID", "anonymous")
        from backend.modules.dna_chain.teleport import teleport
        teleport(request.source, request.destination, reason=request.reason or "api_call")

        MEMORY.store({
            "role": "system",
            "label": "teleport",
            "content": f"Agent {agent_id} teleported from {request.source} to {request.destination} (reason: {request.reason})"
        })
        return {"status": "success", "message": f"Teleported from {request.source} to {request.destination} by {agent_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teleport failed: {e}"}