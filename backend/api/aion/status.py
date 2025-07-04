from fastapi import APIRouter
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.sim.grid_engine import GridWorld

router = APIRouter(prefix="/aion", tags=["AION Status"])

@router.get("/aion/status")
def get_status():
    tracker = MilestoneTracker()
    planner = StrategyPlanner()
    grid = GridWorld()

    return {
        "phase": tracker.get_phase(),
        "milestones": tracker.list_milestones(),
        "unlocked": tracker.list_unlocked_modules(),
        "locked": tracker.list_locked_modules(),
        "strategy_count": len(planner.strategies),
        "grid_progress": grid.get_progress()
    }