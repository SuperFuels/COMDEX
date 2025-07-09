# backend/routes/runtime.py

from fastapi import APIRouter
from backend.modules.runtime.container_runtime import run_glyph_runtime
from backend.modules.consciousness.state_manager import state_manager

router = APIRouter()

@router.post("/api/aion/run-runtime")
def run_runtime_tick():
    """
    Trigger a glyph runtime execution cycle (AION tick).
    """
    print("🌀 [Runtime] Executing glyph runtime tick...")
    
    run_glyph_runtime(state_manager)

    return {
        "status": "✅ Glyph runtime tick executed",
        "message": "AION has processed glyphs for this cycle"
    }