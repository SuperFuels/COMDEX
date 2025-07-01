# ✅ Step 1: Create backend route to log game events (aion/game-event)

# File: backend/routes/aion_game.py
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


# ✅ Step 2: Create backend route to serve goal (aion/goal)

@router.get("/aion/goal")
async def get_current_goal():
    return {"goal": "Explore the world and collect coins"}


# ✅ Step 3: Mount these routes in main.py if not already
# File: backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.import aion_game  # Make sure import path is correct

app = FastAPI()

# CORS for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount router
app.include_router(aion_game.router)