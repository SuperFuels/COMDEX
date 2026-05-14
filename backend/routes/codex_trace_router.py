# File: backend/routes/codex_trace_router.py

from fastapi import APIRouter
from ..modules.glyphos.codex_trace_bridge import codex_trace

router = APIRouter()

@router.get("/codex/trace")
def get_codex_trace():
    return {
        "status": "ok",
        "trace": codex_trace.get_trace()
    }