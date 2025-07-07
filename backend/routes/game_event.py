from fastapi import APIRouter, Request
from pydantic import BaseModel

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

class GameEvent(BaseModel):
    event: str
    metadata: dict = {}

@router.post("/aion/game-event")
async def handle_game_event(event: GameEvent, request: Request):
    print(f"Event received: {event.event}, Metadata: {event.metadata}")
    return {"status": "ok"}