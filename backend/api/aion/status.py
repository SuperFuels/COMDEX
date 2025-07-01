from fastapi import APIRouter
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.strategy_planner import StrategyPlanner
from modules.sim.grid_engine import GridWorld

router = APIRouter()

@router.get("/aion/status")
def get_status():
    tracker = MilestoneTracker()
    planner = StrategyPlanner()
    grid = GridWorld()

    return {
        "phase": tracker.get_phase(),
        "milestones": tracker.get_milestones(),
        "unlocked": tracker.get_unlocked_modules(),
        "locked": tracker.get_locked_modules(),
        "strategy_count": len(planner.strategies),
        "grid_progress": grid.get_progress()
    }
