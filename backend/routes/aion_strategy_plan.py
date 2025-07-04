from fastapi import APIRouter
from backend.modules.skills.strategy_planner import StrategyPlanner

router = APIRouter()

@router.get("/api/aion/strategy-plan")
def get_strategy_plan():
    planner = StrategyPlanner()
    return {"strategies": planner.strategies}
