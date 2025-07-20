from fastapi import APIRouter
from backend.modules.tessaris.tessaris_engine import TessarisEngine

router = APIRouter()
tessaris = TessarisEngine()

@router.get("/aion/tessaris-intents")  # ✅ Only /aion/... (not /api/aion/...)
async def get_tessaris_intents():
    return tessaris.intent_queue