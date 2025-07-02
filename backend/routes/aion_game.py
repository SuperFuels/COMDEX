from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime
import logging

router = APIRouter()

# In-memory log (can be replaced with DB later)
game_events = []

class GameEvent(BaseModel):
    event: str
    metadata: dict = {}
    timestamp: datetime = datetime.utcnow()

@router.post("/aion/game-event")
async def log_game_event(event: GameEvent):
    game_events.append(event)
    logging.info(f"[AION GAME EVENT] {event.event} - {event.metadata}")
    return {"status": "ok", "logged": event.event}

@router.get("/aion/game-event")
async def get_all_events():
    return {"events": game_events}

@router.get("/aion/goal")
async def get_current_goal():
    return {"goal": "Explore the world and collect coins"}