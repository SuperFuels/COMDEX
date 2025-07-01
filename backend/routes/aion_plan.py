from fastapi import APIRouter
from fastapi.responses import JSONResponse

from modules.skills.strategy_planner import StrategyPlanner

router = APIRouter()

@router.get("/aion/strategy-plan")
async def get_strategy_plan():
    try:
        planner = StrategyPlanner()
        goals = planner.generate()
        return JSONResponse(content={"strategy": goals})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
