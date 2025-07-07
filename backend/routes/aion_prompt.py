from fastapi import APIRouter
from pydantic import BaseModel
from backend.modules.skills.aion_prompt_engine import build_prompt_context
import openai
import os
import logging

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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
        usage = response["usage"]
        tokens_used = usage["total_tokens"]
        estimated_cost = round((tokens_used / 1000) * 0.03, 4)  # GPT-4 8k input cost estimate

        logger.info(f"💬 AION replied: {aion_reply}")
        return {
            "reply": aion_reply,
            "tokens_used": tokens_used,
            "cost_estimate": estimated_cost
        }

    except Exception as e:
        logger.error("❌ AION prompt error", exc_info=True)
        return {
            "error": f"AION error: {type(e).__name__}: {str(e)}"
        }