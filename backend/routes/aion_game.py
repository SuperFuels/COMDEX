from fastapi import APIRouter, Request
from pydantic import BaseModel
from modules.skills.memory_engine import MemoryEngine
from modules.skills.strategy_planner import StrategyPlanner

router = APIRouter()
memory_engine = MemoryEngine()
planner = StrategyPlanner()

class GameEvent(BaseModel):
    type: str
    description: str
    value: int

@router.post("/game-event")
async def log_game_event(event: GameEvent):
    memory_engine.store_memory({
        "source": "game",
        "event": event.type,
        "description": event.description,
        "value": event.value
    })
    return {"status": "✅ Logged"}

@router.get("/goal")
async def get_current_goal():
    goal = planner.get_current_goal()
    return {"goal": goal}

@router.post("/goal/next")
async def generate_next_goal():
    new_goal = planner.generate_goal()
    memory_engine.store_memory({
        "source": "goal",
        "type": "generated",
        "content": new_goal
    })
    return {"new_goal": new_goal}