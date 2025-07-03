# routes/aion_goals.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from modules.skills.goal_tracker import GoalTracker

router = APIRouter()
goal_tracker = GoalTracker()

class CompleteGoalRequest(BaseModel):
    name: str

class EditGoalRequest(BaseModel):
    old_name: str
    new_name: str

@router.get("/aion/goals")
async def get_goals():
    goals = goal_tracker.get_goals()
    # Adapt keys for frontend if needed: ensure consistent naming
    adapted_goals = [
        {
            "name": g.get("name"),
            "status": g.get("status"),
            "description": g.get("description", ""),
            "reward": g.get("reward"),
            "completed_at": g.get("completed_at", None),
            "created_at": g.get("created_at", None),
        }
        for g in goals
    ]
    return {"goals": adapted_goals}

@router.post("/aion/goals/complete")
async def complete_goal(req: CompleteGoalRequest):
    goals = goal_tracker.get_goals()
    for idx, goal in enumerate(goals):
        if goal.get("name") == req.name:
            updated = goal_tracker.update_goal(idx, "completed")
            if updated:
                return {"message": f"Goal '{req.name}' marked as completed."}
            else:
                raise HTTPException(status_code=500, detail="Failed to update goal status")
    raise HTTPException(status_code=404, detail="Goal not found")

@router.post("/aion/goals/edit")
async def edit_goal(req: EditGoalRequest):
    goals = goal_tracker.get_goals()
    for goal in goals:
        if goal.get("name") == req.old_name:
            goal["name"] = req.new_name
            goal_tracker.save_goals()
            return {"message": f"Goal renamed from '{req.old_name}' to '{req.new_name}'."}
    raise HTTPException(status_code=404, detail="Goal not found")