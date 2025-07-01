from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import openai
import os

from modules.skills.aion_prompt_engine import build_prompt_context
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.goal_tracker import GoalTracker  # ✅ NEW

router = APIRouter()

openai.api_key = os.getenv("OPENAI_API_KEY")

class AIONRequest(BaseModel):
    prompt: str

@router.post("/aion")
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

        # Attempt to extract goals from reply
        goal_tracker = GoalTracker()
        for line in reply.splitlines():
            if line.strip().lower().startswith("goal:"):
                goal_text = line.split(":", 1)[1].strip()
                goal_tracker.add_goal(goal_text)

        return {"reply": reply}

    except Exception as e:
        return {"reply": f"❌ AION error: {str(e)}"}


@router.get("/aion/status")
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