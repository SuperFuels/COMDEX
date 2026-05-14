# -*- coding: utf-8 -*-
# backend/routes/api/aion_api.py
from __future__ import annotations

import os
import json
import logging
import subprocess

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import openai

# Core modules
from backend.modules.skills.aion_prompt_engine import build_prompt_context
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.goal_tracker import GoalTracker
from backend.modules.command_registry import resolve_command, list_commands as get_command_registry
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.consciousness.state_manager import StateManager  # ✅ For container listing

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Track this file for upgrades

# -----------------------
# Setup
# -----------------------
router = APIRouter(prefix="/api/aion", tags=["AION"])
logger = logging.getLogger("comdex")

openai.api_key = os.getenv("OPENAI_API_KEY")
logger.info("OpenAI API Key loaded: %s", "Yes" if openai.api_key else "No")


# -----------------------
# Models
# -----------------------
class AIONRequest(BaseModel):
    prompt: str


class GoalCreateRequest(BaseModel):
    title: str
    description: str


# -----------------------
# Routes
# -----------------------
@router.post("/")
async def ask_aion(request: AIONRequest):
    """Ask AION a question using GPT and track milestones + goals."""
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

        estimated_cost = None
        if tokens_used:
            cost_per_1k = 0.03
            estimated_cost = round((tokens_used / 1000) * cost_per_1k, 4)

        # Milestones
        tracker = MilestoneTracker()
        tracker.detect_milestones_from_dream(reply)

        # Goals
        goal_tracker = GoalTracker()
        for line in reply.splitlines():
            if line.strip().lower().startswith("goal:"):
                goal_text = line.split(":", 1)[1].strip()
                goal_tracker.add_goal(goal_text)

        return {
            "reply": reply,
            "tokens_used": tokens_used,
            "cost_estimate": f"${estimated_cost}" if estimated_cost else None,
            "model": response.model,
        }
    except Exception as e:
        return {"reply": f"❌ AION error: {e}"}


@router.get("/status")
async def get_aion_status():
    """Return milestone phase, unlocked/locked modules, and milestones."""
    try:
        tracker = MilestoneTracker()
        return JSONResponse(content={
            "phase": tracker.get_phase(),
            "unlocked": tracker.list_unlocked_modules(),
            "locked": tracker.list_locked_modules(),
            "milestones": tracker.list_milestones(),
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/strategy-plan")
async def get_strategy_plan():
    """Generate a strategy plan using the StrategyPlanner."""
    try:
        from backend.modules.skills.strategy_planner import StrategyPlanner
        planner = StrategyPlanner()
        planner.generate()
        return JSONResponse(content={"strategy": planner.strategies})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/current-goal")
async def get_current_goal():
    """Return the current generated goal from StrategyPlanner."""
    try:
        from backend.modules.skills.strategy_planner import StrategyPlanner
        planner = StrategyPlanner()
        return JSONResponse(content={"current_goal": planner.generate_goal()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/goals")
async def get_saved_goals():
    """List saved goals from MilestoneTracker."""
    try:
        tracker = MilestoneTracker()
        return JSONResponse(content={"goals": tracker.list_saved_goals()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/goals")
async def create_goal(goal: GoalCreateRequest):
    """Create a new goal and its milestone."""
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
    """Return learned skills from disk (learned_skills.json)."""
    try:
        skills_path = os.path.join("backend", "modules", "skills", "learned_skills.json")
        with open(skills_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to load learned skills: {e}"})


@router.post("/learning-cycle")
async def run_learning_cycle():
    """Trigger the learning cycle script."""
    try:
        result = subprocess.run(
            ["python", "backend/scripts/aion_learning_cycle.py"],
            capture_output=True,
            text=True,
            check=True,
        )
        return JSONResponse(content={"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": e.stderr or str(e)})


@router.get("/commands")
async def list_commands_api():
    """Return all available registered commands."""
    return get_command_registry()


@router.post("/sync-messages")
async def sync_terminal_messages(request: Request):
    """
    Accepts a list of messages from the frontend terminal and logs them to AION memory.
    Each message should include: role, content, and optional status.
    """
    body = await request.json()
    messages = body.get("messages", [])

    if not messages or not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="No valid messages provided")

    for msg in messages:
        content = msg.get("content")
        if content:
            MemoryEngine.store({
                "content": content,
                "role": msg.get("role", "unknown"),
                "tags": ["terminal_sync"],
            })

    return {"status": "success", "message_count": len(messages)}


@router.get("/containers")
async def list_available_containers():
    """Return all known .dc containers with in-memory status."""
    try:
        state = StateManager()
        return JSONResponse(content={"containers": state.list_containers_with_status()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})