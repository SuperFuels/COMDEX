# backend/routes/aion_goals.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.modules.skills.goal_tracker import GoalTracker

router = APIRouter(prefix="/aion", tags=["AION Goals"])
goal_tracker = GoalTracker()

class CompleteGoalRequest(BaseModel):
    name: str

class EditGoalRequest(BaseModel):
    old_name: str
    new_name: str

@router.get("/goals")
async def get_goals():
    goals = goal_tracker.get_goals()
    return {"goals": goals}

@router.get("/current-goal")
async def get_current_goal():
    goals = goal_tracker.get_goals()
    for g in goals:
        if g.get("status") != "completed":
            return {
                "name": g.get("name"),
                "status": g.get("status"),
                "description": g.get("description", ""),
                "reward": g.get("reward"),
                "created_at": g.get("created_at", None),
            }
    return {"message": "🎉 All goals completed."}

@router.post("/goals/complete")
async def complete_goal(req: CompleteGoalRequest):
    goals = goal_tracker.get_goals()
    for idx, goal in enumerate(goals):
        if goal.get("name") == req.name:
            updated = goal_tracker.update_goal(idx, "completed")
            if updated:
                unlocked_skills = goal_tracker.unlock_skills_for_goal(req.name)
                unlocked_milestones = goal_tracker.unlock_milestones_for_goal(req.name)
                return {
                    "message": f"Goal '{req.name}' marked as completed.",
                    "unlocked_skills": unlocked_skills,
                    "unlocked_milestones": unlocked_milestones,
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to update goal status")
    raise HTTPException(status_code=404, detail="Goal not found")

@router.post("/goals/edit")
async def edit_goal(req: EditGoalRequest):
    goals = goal_tracker.get_goals()
    for goal in goals:
        if goal.get("name") == req.old_name:
            goal["name"] = req.new_name
            goal_tracker.save_goals()
            return {"message": f"Goal renamed from '{req.old_name}' to '{req.new_name}'."}
    raise HTTPException(status_code=404, detail="Goal not found")