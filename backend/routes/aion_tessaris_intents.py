# File: backend/routes/aion_tessaris_intents.py

from fastapi import APIRouter
from backend.modules.tessaris.tessaris_engine import TESSARIS_ENGINE

router = APIRouter()

@router.get("/aion/tessaris-intents")
async def get_tessaris_intents():
    """
    Returns the current Tessaris intent queue as a list.
    """
    return TESSARIS_ENGINE.intent_queue