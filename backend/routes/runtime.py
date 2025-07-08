# routes/runtime.py
from fastapi import APIRouter
from backend.modules.runtime.container_runtime import run_glyph_runtime
from backend.modules.consciousness.state_manager import state_manager

router = APIRouter()

@router.post("/api/aion/runtime/tick")
def runtime_tick():
    run_glyph_runtime(state_manager)
    return {"status": "Glyph runtime tick executed"}