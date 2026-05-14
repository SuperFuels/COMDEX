from fastapi import APIRouter
from backend.replay.photon_journal import append_event, load_events

router = APIRouter()

@router.post("/replay/append")
async def append_replay(ev: dict):
    append_event(ev)
    return {"ok": True}

@router.get("/replay/all")
async def get_replay():
    return list(load_events())