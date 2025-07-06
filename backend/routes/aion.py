from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import openai
import os
import logging
import json
import subprocess  # ✅ For learning-cycle execution

from backend.modules.skills.aion_prompt_engine import build_prompt_context
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.goal_tracker import GoalTracker
from backend.modules.commands_registry import get_command_registry  # ✅ NEW

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

        usage = response.usage
        tokens_used = usage.total_tokens if usage else None
        cost_per_1k = 0.03
        estimated_cost = round((tokens_used / 1000) * cost_per_1k, 4) if tokens_used else None

        tracker = MilestoneTracker()
        tracker.detect_milestones_from_dream(reply)

        goal_tracker = GoalTracker()
        for line in reply.splitlines():
            if line.strip().lower().startswith("goal:"):
                goal_text = line.split(":", 1)[1].strip()
                goal_tracker.add_goal(goal_text)

        return {
            "reply": reply,
            "tokens_used": tokens_used,
            "cost_estimate": f"${estimated_cost}",
            "model": response.model,
        }

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


@router.get("/learned-skills")
async def get_learned_skills():
    try:
        skills_path = os.path.join("backend", "modules", "skills", "learned_skills.json")
        with open(skills_path, "r", encoding="utf-8") as f:
            skills = json.load(f)
        return JSONResponse(content=skills)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to load learned skills: {str(e)}"})


@router.post("/learning-cycle")
async def run_learning_cycle():
    try:
        result = subprocess.run(
            ["python", "backend/scripts/aion_learning_cycle.py"],
            capture_output=True,
            text=True,
            check=True
        )
        return JSONResponse(content={
            "status": "success",
            "output": result.stdout
        })
    except subprocess.CalledProcessError as e:
        return JSONResponse(status_code=500, content={
            "status": "error",
            "error": e.stderr or str(e)
        })


# ✅ NEW: Return global command registry
@router.get("/commands")
async def list_commands():
    return get_command_registry()