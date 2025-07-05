from fastapi import APIRouter
from pydantic import BaseModel
from backend.modules.skills.aion_prompt_engine import build_prompt_context
from openai import OpenAI
import os

router = APIRouter()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PromptRequest(BaseModel):
    prompt: str

@router.post("/aion/prompt")
async def prompt_aion(req: PromptRequest):
    """
    Accepts a user prompt and returns AION's response using dynamic context.
    """
    try:
        messages = build_prompt_context(req.prompt)

        response = openai_client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=messages,
            temperature=0.8
        )

        aion_reply = response.choices[0].message.content.strip()
        return {"reply": aion_reply}

    except Exception as e:
        return {"error": f"AION error: {str(e)}"}