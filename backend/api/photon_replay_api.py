# ============================================================
# 🌐 API: Photon Resonance Timeline Replay
# ============================================================

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import asyncio

from backend.modules.photonlang.integrations.photon_timeline_replay import (
    list_available_snapshots,
    replay_timeline,
)

router = APIRouter(prefix="/api/photon", tags=["photon-replay"])


@router.get("/replay_timeline")
async def replay_timeline_route(
    limit: int = Query(5, ge=1, le=50),
    broadcast: bool = Query(True),
    delay: float = Query(0.8, ge=0.0, le=5.0),
    reinjection: bool = Query(True, description="Whether to reinject workspace + SCI state"),
    container_id: Optional[str] = Query("default_sci_session"),
):
    """
    Replay the most recent Photon Telemetry snapshots (.ptn)
    through the runtime stack (Photon -> SQI -> QQC -> QFC),
    and optionally reinject state into the live SCI workspace.
    """
    try:
        frames = await replay_timeline(
            limit=limit,
            broadcast=broadcast,
            delay=delay,
            reinject=reinjection,
            container_id=container_id,
        )
        return JSONResponse(content={"ok": True, "frames": frames})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {e}")


@router.get("/available_snapshots")
async def list_snapshots_route(limit: int = Query(10, ge=1, le=50)):
    """List available .ptn telemetry files for replay."""
    try:
        snapshots = list_available_snapshots(limit)
        return {"snapshots": snapshots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list snapshots: {e}")