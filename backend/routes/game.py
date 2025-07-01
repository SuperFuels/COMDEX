from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class GameEvent(BaseModel):
    event: str
    metadata: dict = {}

@router.post("/aion/game-event")
async def log_game_event(event: GameEvent):
    # Optional: store to database or log to file
    print(f"[AION EVENT] {event.event} — {event.metadata}")
    return {"status": "ok"}