# 📁 backend/routes/codex_scroll.py

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.modules.codex.codex_emulator import CodexEmulator
from backend.modules.hexcore.memory_engine import MEMORY

router = APIRouter()
emulator = CodexEmulator()

class ScrollRequest(BaseModel):
    scroll: str
    context: Optional[Dict[str, Any]] = {}

@router.post("/codex/scroll")
async def run_scroll(request: ScrollRequest):
    try:
        result = emulator.run(request.scroll, request.context)

        MEMORY.store({
            "label": "codex_scroll_execution",
            "type": "scroll",
            "scroll": request.scroll,
            "context": request.context,
            "result": result
        })

        return {
            "status": "ok",
            "scroll": request.scroll,
            "result": result
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }