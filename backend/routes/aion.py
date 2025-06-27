from fastapi import APIRouter, Request
from backend.modules.skills.aion_prompt_engine import AION

router = APIRouter()
aion = AION()

@router.post("/aion/prompt")
async def process_prompt(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")

    if not prompt:
        return {"reply": "⚠️ No prompt provided."}

    reply = aion.respond(prompt)
    return {"reply": reply}
