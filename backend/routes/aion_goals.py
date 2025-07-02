# File: backend/routes/aion_goals.py

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.strategy_planner import StrategyPlanner
from datetime import datetime

router = APIRouter()

@router.get("/aion/goals")
async def get_saved_goals():
    """
    🔄 Return all saved goals from milestones, formatted for frontend display.
    """
    try:
        tracker = MilestoneTracker()
        raw_goals = tracker.list_saved_goals()

        # Convert to structured list
        formatted_goals = []
        for g in raw_goals:
            formatted_goals.append({
                "name": g.strip()[:100],
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "strategy": None  # Placeholder for now
            })

        return JSONResponse(content={"goals": formatted_goals})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/aion/current-goal")
async def get_current_goal():
    """
    🎯 Return the current highest priority goal from the strategy planner.
    """
    try:
        planner = StrategyPlanner()
        goal = planner.generate_goal()
        return JSONResponse(content={"current_goal": goal})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/aion/goals/complete")
async def mark_goal_complete(payload: dict):
    """
    ✅ Mark a specific goal as completed.
    Expects payload: { "name": "Goal Name" }
    """
    try:
        tracker = MilestoneTracker()
        name = payload.get("name")
        if not name:
            return JSONResponse(status_code=400, content={"error": "Missing goal name"})
        result = tracker.mark_goal_completed(name)
        return JSONResponse(content={"message": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/aion/goals/edit")
async def edit_goal(request: Request):
    """
    📝 Edit the name of a goal.
    Expects payload: { "old_name": "Old", "new_name": "New" }
    """
    try:
        body = await request.json()
        tracker = MilestoneTracker()
        old = body.get("old_name")
        new = body.get("new_name")
        if not old or not new:
            return JSONResponse(status_code=400, content={"error": "Missing old or new goal name"})
        result = tracker.edit_goal_name(old, new)
        return JSONResponse(content={"message": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})