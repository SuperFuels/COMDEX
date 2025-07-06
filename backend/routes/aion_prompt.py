from fastapi import APIRouter
from pydantic import BaseModel
from backend.modules.skills.aion_prompt_engine import build_prompt_context
import openai
import os
import logging

router = APIRouter()
logger = logging.getLogger("aion_prompt")

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

class PromptRequest(BaseModel):
    prompt: str

@router.post("/prompt")
async def prompt_aion(req: PromptRequest):
    """
    Accepts a user prompt and returns AION's response using dynamic context.
    """
    try:
        messages = build_prompt_context(req.prompt)
        logger.info(f"🧠 AION prompt received: {req.prompt}")

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.8,
        )

        aion_reply = response.choices[0].message["content"].strip()
        logger.info(f"💬 AION replied: {aion_reply}")
        return {"reply": aion_reply}

    except Exception as e:
        logger.error("❌ AION prompt error", exc_info=True)
        return {"error": f"AION error: {type(e).__name__}: {str(e)}"}