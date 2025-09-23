# -*- coding: utf-8 -*-
"""
Avatar Runtime API
Control the AION Avatar inside a .dc container.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any

from backend.modules.avatar.avatar_core import AIONAvatar

router = APIRouter(prefix="/avatar", tags=["AION Avatar"])

# Default avatar instance
avatar = AIONAvatar(container_id="default")


# ---------- Endpoints ----------
@router.post("/spawn")
async def spawn_avatar() -> Dict[str, Any]:
    try:
        result = avatar.spawn()
        return {"status": "spawned", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/move")
async def move_avatar(request: Request) -> Dict[str, Any]:
    body = await request.json()
    dx = body.get("dx", 0)
    dy = body.get("dy", 0)
    dz = body.get("dz", 0)
    dt = body.get("dt", 0)
    result = avatar.move(dx, dy, dz, dt)
    return {"status": "moved", "result": result}


@router.post("/mode")
async def set_mode(request: Request) -> Dict[str, Any]:
    body = await request.json()
    mode = body.get("mode", "idle")
    result = avatar.set_mode(mode)
    return {"status": "mode_set", "result": result}


@router.post("/tick")
async def tick_avatar() -> Dict[str, Any]:
    result = avatar.tick()
    return {"status": "tick_complete", "result": result}


@router.post("/tick_rate")
async def set_tick_rate(request: Request) -> Dict[str, Any]:
    body = await request.json()
    try:
        rate = float(body.get("rate", 1.0))
        avatar.tick_rate = rate
        return {"status": "tick_rate_updated", "tick_rate": avatar.tick_rate}
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid tick rate")


@router.post("/rollback")
async def rollback_time(request: Request) -> Dict[str, Any]:
    body = await request.json()
    try:
        steps = int(body.get("steps", 1))
        avatar.position["t"] -= steps * avatar.tick_rate
        return {"status": "rolled_back", "new_time": avatar.position["t"]}
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid rollback steps")


@router.post("/set_container")
async def set_container(request: Request) -> Dict[str, Any]:
    body = await request.json()
    container_id = body.get("container_id", "default")
    avatar.container_id = container_id
    avatar.kernel = avatar.kernel.__class__(container_id)  # Reload kernel
    return {"status": "container_updated", "container": container_id}


@router.get("/state")
async def get_avatar_state() -> JSONResponse:
    return JSONResponse(content=avatar.state())


@router.get("/trace_log")
async def get_trace_log() -> JSONResponse:
    try:
        return JSONResponse(content={"trace": avatar.trace_log[-100:]})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trace fetch failed: {str(e)}")


@router.get("/runtime_tick_summary")
async def get_runtime_tick_summary() -> Dict[str, Any]:
    try:
        return {
            "tick": avatar.tick_count,
            "position": avatar.position,
            "active_glyphs": avatar.active_glyphs,
            "mode": avatar.mode,
            "container": avatar.container_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary fetch failed: {str(e)}")