from fastapi import APIRouter, HTTPException, Request
from typing import Any, Dict
from datetime import datetime, timezone
import asyncio

# engines + utils
from backend.modules.dimensions.time_controller import TimeController
from backend.modules.dna_chain.dc_handler import load_dc_container
from backend.events.ghx_bus import broadcast

router = APIRouter(tags=["AION Time"])

TIME = TimeController()

# Simple runners for /play
PLAYERS: Dict[str, asyncio.Task] = {}
PLAY_CFG: Dict[str, Dict[str, Any]] = {}   # { cid: {"ratio": float, "running": bool} }
BASE_INTERVAL = 1.0  # seconds/tick at 1.0x

def _interval_from_ratio(ratio: float) -> float:
    r = max(0.01, float(ratio))
    return BASE_INTERVAL / r

async def _run_player(cid: str):
    while PLAY_CFG.get(cid, {}).get("running"):
        # best-effort snapshot from disk
        try:
            dc = load_dc_container(cid)
        except Exception:
            dc = {"id": cid, "type": "container", "glyphs": [], "meta": {}}

        # advance and store snapshot
        TIME.tick(cid, dc)

        # notify UIs
        await broadcast(cid, {
            "type": "time_update",
            "container_id": cid,
            "tick": TIME.get_tick(cid),
            "status": TIME.get_status(cid),
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(_interval_from_ratio(PLAY_CFG[cid].get("ratio", 1.0)))

@router.get("/time/{container_id}/status")
def get_status(container_id: str) -> Dict[str, Any]:
    cid = container_id.strip()
    st = TIME.get_status(cid)
    st["playing"] = PLAY_CFG.get(cid, {}).get("running", False)
    st["ratio"] = PLAY_CFG.get(cid, {}).get("ratio", 1.0)
    st["snapshots"] = len(TIME.snapshots[cid])
    st["tick"] = TIME.get_tick(cid)
    return st

@router.post("/time/{container_id}/tick")
async def do_tick(container_id: str) -> Dict[str, Any]:
    cid = container_id.strip()
    try:
        dc = load_dc_container(cid)
    except Exception:
        dc = {"id": cid, "type": "container", "glyphs": [], "meta": {}}

    TIME.tick(cid, dc)

    await broadcast(cid, {
        "type": "time_update",
        "container_id": cid,
        "tick": TIME.get_tick(cid),
        "status": TIME.get_status(cid),
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "tick": TIME.get_tick(cid)}

@router.post("/time/{container_id}/rewind")
async def rewind(container_id: str, req: Request) -> Dict[str, Any]:
    cid = container_id.strip()
    body = await req.json()
    target = int(body.get("tick", 0))

    snap = TIME.rewind(cid, target)
    if snap is None:
        raise HTTPException(400, f"No snapshot at tick {target}")

    await broadcast(cid, {
        "type": "time_update",
        "container_id": cid,
        "tick": TIME.get_tick(cid),
        "status": TIME.get_status(cid),
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "tick": TIME.get_tick(cid)}

@router.post("/time/{container_id}/play")
async def play(container_id: str, req: Request) -> Dict[str, Any]:
    cid = container_id.strip()
    body = await req.json()
    ratio = float(body.get("ratio", 1.0))

    # stop existing
    await pause(container_id)

    # start new
    PLAY_CFG[cid] = {"ratio": ratio, "running": True}
    PLAYERS[cid] = asyncio.get_event_loop().create_task(_run_player(cid))

    await broadcast(cid, {
        "type": "time_update",
        "container_id": cid,
        "tick": TIME.get_tick(cid),
        "status": TIME.get_status(cid),
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "playing": True, "ratio": ratio}

@router.post("/time/{container_id}/pause")
async def pause(container_id: str) -> Dict[str, Any]:
    cid = container_id.strip()

    cfg = PLAY_CFG.get(cid)
    if cfg:
        cfg["running"] = False

    task = PLAYERS.pop(cid, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except Exception:
            pass

    await broadcast(cid, {
        "type": "time_update",
        "container_id": cid,
        "tick": TIME.get_tick(cid),
        "status": TIME.get_status(cid),
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "playing": False}

@router.post("/time/{container_id}/loop")
async def set_loop(container_id: str, req: Request) -> Dict[str, Any]:
    """
    Body: { "enabled": bool, "start"?: int, "end"?: int }
    """
    cid = container_id.strip()
    body = await req.json()
    if body.get("enabled"):
        start = int(body.get("start", 0))
        end = int(body.get("end", max(1, TIME.get_tick(cid))))
        TIME.enable_loop(cid, start, end)
    else:
        TIME.disable_loop(cid)

    await broadcast(cid, {
        "type": "time_update",
        "container_id": cid,
        "tick": TIME.get_tick(cid),
        "status": TIME.get_status(cid),
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "status": TIME.get_status(cid)}

@router.post("/time/{container_id}/decay")
async def set_decay(container_id: str, req: Request) -> Dict[str, Any]:
    """
    Body: { "enabled": bool }
    """
    cid = container_id.strip()
    body = await req.json()
    enabled = bool(body.get("enabled", False))
    if enabled:
        TIME.enable_decay(cid)
    else:
        TIME.disable_decay(cid)

    await broadcast(cid, {
        "type": "time_update",
        "container_id": cid,
        "tick": TIME.get_tick(cid),
        "status": TIME.get_status(cid),
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "status": TIME.get_status(cid)}