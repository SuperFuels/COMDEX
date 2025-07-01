from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class GameEvent(BaseModel):
    event: str
    metadata: dict = {}

@router.post("/api/aion/game-event")
async def handle_game_event(event: GameEvent, request: Request):
    print(f"Event received: {event.event}, Metadata: {event.metadata}")
    return {"status": "ok"}