from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.modules.skills.strategy_planner import StrategyPlanner

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

@router.get("/aion/strategy-plan")
async def get_strategy_plan():
    try:
        planner = StrategyPlanner()
        planner.generate()  # Ensure latest strategies generated

        # Deduplicate by goal+action
        unique_strategies = {}
        for s in planner.strategies:
            key = (s.get("goal"), s.get("action"))
            if key not in unique_strategies:
                unique_strategies[key] = s

        # Sort by priority descending and limit to top 10
        sorted_strategies = sorted(
            unique_strategies.values(),
            key=lambda x: x.get("priority", 0),
            reverse=True
        )[:10]

        return JSONResponse(content={"strategy": sorted_strategies})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/aion/current-goal")
async def get_current_goal():
    try:
        planner = StrategyPlanner()
        goal = planner.generate_goal()
        return JSONResponse(content={"current_goal": goal})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})