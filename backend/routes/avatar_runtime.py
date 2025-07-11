"""
Avatar Runtime API
Control the AION Avatar inside a .dc container.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from modules.dimensions.avatar_core import AIONAvatar

router = APIRouter()
avatar = AIONAvatar(container_id="default")  # Load default container

@router.post("/avatar/spawn")
async def spawn_avatar():
    result = avatar.spawn()
    return {"status": "spawned", "result": result}

@router.post("/avatar/move")
async def move_avatar(request: Request):
    body = await request.json()
    dx = body.get("dx", 0)
    dy = body.get("dy", 0)
    dz = body.get("dz", 0)
    dt = body.get("dt", 0)
    result = avatar.move(dx, dy, dz, dt)
    return {"status": "moved", "result": result}

@router.post("/avatar/mode")
async def set_mode(request: Request):
    body = await request.json()
    mode = body.get("mode", "idle")
    result = avatar.set_mode(mode)
    return {"status": "mode_set", "result": result}

@router.post("/avatar/tick")
async def tick_avatar():
    result = avatar.tick()
    return {"status": "tick_complete", "result": result}

@router.get("/avatar/state")
async def get_avatar_state():
    return JSONResponse(content=avatar.state())
