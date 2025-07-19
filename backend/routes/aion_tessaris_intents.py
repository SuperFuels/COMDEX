# ✅ File: backend/routes/aion_tessaris_intents.py

from fastapi import APIRouter
from backend.modules.tessaris.tessaris_engine import TESSARIS_ENGINE

router = APIRouter()

@router.get("/aion/tessaris-intents")  # ✅ Only /aion/... (not /api/aion/...)
async def get_tessaris_intents():
    return TESSARIS_ENGINE.intent_queue