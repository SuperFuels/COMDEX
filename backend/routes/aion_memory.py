# File: backend/routes/aion_memory.py
# 🧠 AION Memory API — access short-term resonance history and Φ-summary

from fastapi import APIRouter
from backend.modules.aion_resonance.conversation_memory import MEMORY

router = APIRouter()

@router.get("/memory")
async def get_conversation_memory():
    """
    Return AION's short-term conversation memory and resonance summary.
    """
    try:
        memory_data = MEMORY.get_recent()
        return {
            "status": "ok",
            "memory": memory_data
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}