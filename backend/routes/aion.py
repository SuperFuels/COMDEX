from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from dotenv import load_dotenv

from openai import OpenAI
from backend.modules.skills.aion_prompt_engine import build_prompt_context
from backend.modules.skills.milestone_tracker import MilestoneTracker
import subprocess

# Load environment variables from .env.local if present
env_path = Path(__file__).resolve().parents[3] / ".env.local"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Initialize OpenAI client with new SDK style
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

AION_API_KEY = os.getenv("AION_API_KEY")  # Secret API key for /run-dream

router = APIRouter(prefix="/aion")

class AIONRequest(BaseModel):
    prompt: str

@router.post("/prompt")
async def ask_aion(request: AIONRequest):
    try:
        messages = build_prompt_context(request.prompt)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
        )

        reply = response.choices[0].message.content.strip()

        tracker = MilestoneTracker()
        tracker.detect_milestones_from_dream(reply)

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

@router.post("/run-dream")
def trigger_dream_cycle(x_api_key: str = Header(...)):
    if x_api_key != AION_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key")

    try:
        print("🌙 Cloud Scheduler triggered AION dream cycle...")
        subprocess.run(["python", "backend/modules/skills/dream_core.py"], check=True)
        return {"status": "dream cycle triggered"}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "details": str(e)}