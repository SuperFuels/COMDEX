# File: backend/routes/aion_prompt.py

from fastapi import APIRouter
from pydantic import BaseModel
import openai
import os
import logging

from backend.modules.skills.aion_prompt_engine import build_prompt_context

# ✅ DNA Switch registration
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Logger setup
logger = logging.getLogger("aion_prompt")

# ✅ API Router
router = APIRouter()

# ✅ Set OpenAI API key securely
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.warning("⚠️ OPENAI_API_KEY not set in environment. Requests will fail.")

# ✅ Pydantic model for request
class PromptRequest(BaseModel):
    prompt: str

# ✅ Route: /prompt
@router.post("/prompt")
async def prompt_aion(req: PromptRequest):
    """
    Accepts a user prompt and returns AION's response using dynamic context.
    """
    try:
        messages = build_prompt_context(req.prompt)
        logger.info(f"🧠 Received prompt: {req.prompt}")

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.8,
        )

        reply = response.choices[0].message["content"].strip()
        tokens_used = response["usage"]["total_tokens"]
        estimated_cost = round((tokens_used / 1000) * 0.03, 4)  # $0.03 per 1K GPT-4 tokens

        logger.info(f"💬 AION response: {reply} (Tokens: {tokens_used}, Cost: ${estimated_cost})")

        return {
            "reply": reply,
            "tokens_used": tokens_used,
            "cost_estimate": estimated_cost
        }

    except Exception as e:
        logger.error("❌ AION error during prompt handling", exc_info=True)
        return {
            "error": f"AION error: {type(e).__name__}: {str(e)}"
        }