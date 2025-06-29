from fastapi import APIRouter, Request
from backend.modules.sim.grid_engine import GridWorld
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner

router = APIRouter()

@router.post("/aion/grid-loop")
async def run_grid_loop(request: Request):
    # Optional: allow only internal requests (e.g., Cloud Scheduler)
    if "X-Appengine-Cron" not in request.headers:
        return {"error": "Unauthorized"}, 403

    grid = GridWorld()
    tracker = MilestoneTracker()
    planner = StrategyPlanner()

    result = grid.step()

    if result.get("complete"):
        tracker.mark_milestone("grid_world_complete")
        planner.add_strategy("Design next environment for embodiment")

    return {"status": "loop complete", "result": result}
