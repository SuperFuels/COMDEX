from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import openai
import os
import logging

from backend.modules.skills.aion_prompt_engine import build_prompt_context
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.goal_tracker import GoalTracker

router = APIRouter()

logger = logging.getLogger("comdex")

openai.api_key = os.getenv("OPENAI_API_KEY")
logger.info(f"OpenAI API Key loaded: {'Yes' if openai.api_key else 'No'}")

class AIONRequest(BaseModel):
    prompt: str

class GoalCreateRequest(BaseModel):
    title: str
    description: str

@router.post("/")
async def ask_aion(request: AIONRequest):
    try:
        messages = build_prompt_context(request.prompt)

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
        )

        reply = response.choices[0].message["content"]

        # Detect milestones from reply
        tracker = MilestoneTracker()
        tracker.detect_milestones_from_dream(reply)

        # Extract goals from reply lines
        goal_tracker = GoalTracker()
        for line in reply.splitlines():
            if line.strip().lower().startswith("goal:"):
                goal_text = line.split(":", 1)[1].strip()
                goal_tracker.add_goal(goal_text)

        return {"reply": reply}

    except Exception as e:
        return {"reply": f"❌ AION error: {str(e)}"}

@router.get("/status")
async def get_aion_status():
    try:
        tracker = MilestoneTracker()
        summary = {
            "phase": tracker.get_phase(),
            "unlocked": tracker.list_unlocked_modules(),
            "locked": tracker.list_locked_modules(),
            "milestones": tracker.list_milestones(),
        }
        return JSONResponse(content=summary)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/strategy-plan")
async def get_strategy_plan():
    try:
        from backend.modules.skills.strategy_planner import StrategyPlanner
        planner = StrategyPlanner()
        planner.generate()
        return JSONResponse(content={"strategy": planner.strategies})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/current-goal")
async def get_current_goal():
    try:
        from backend.modules.skills.strategy_planner import StrategyPlanner
        planner = StrategyPlanner()
        current_goal = planner.generate_goal()
        return JSONResponse(content={"current_goal": current_goal})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/goals")
async def get_saved_goals():
    try:
        tracker = MilestoneTracker()
        goals = tracker.list_saved_goals()
        return JSONResponse(content={"goals": goals})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/goals/")
async def create_goal(goal: GoalCreateRequest):
    try:
        goal_tracker = GoalTracker()
        created_goal = goal_tracker.create_goal(title=goal.title, description=goal.description)

        milestone_tracker = MilestoneTracker()
        milestone_tracker.create_milestone_for_goal(created_goal)

        return {"status": "success", "goal": created_goal}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})