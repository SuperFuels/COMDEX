from fastapi import APIRouter
from backend.modules.skills.strategy_planner import StrategyPlanner

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

@router.get("/api/aion/strategy-plan")
def get_strategy_plan():
    planner = StrategyPlanner()
    return {"strategies": planner.strategies}
