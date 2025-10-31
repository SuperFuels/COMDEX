# backend/routes/replay_apply.py

from fastapi import APIRouter, HTTPException
from backend.replay.reducer import ReplayReducer

router = APIRouter(prefix="/api/replay", tags=["replay"])

@router.post("/apply")
async def apply_replay(payload: dict):
    frames = payload.get("frames")
    if not isinstance(frames, list):
        raise HTTPException(status_code=400, detail="frames must be a list")

    try:
        # base state is empty; reducer composes full state from logs
        base = {}
        state = ReplayReducer.apply_state(base, frames)
        return {"ok": True, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))