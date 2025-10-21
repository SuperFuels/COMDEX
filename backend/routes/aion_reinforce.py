# File: backend/routes/aion_reinforce.py
# 🌱 API endpoints for AION cognitive reinforcement

from fastapi import APIRouter
from backend.modules.aion_resonance.phi_reinforce import (
    reinforce_from_memory, get_reinforce_state, reset_reinforce_state
)

router = APIRouter()

@router.post("/reinforce")
async def run_reinforcement_cycle():
    """Trigger a cognitive reinforcement pass from recent Φ-memory."""
    state = reinforce_from_memory()
    return {"status": "ok", "baseline": state}

@router.get("/reinforce")
async def get_reinforce_status():
    """View current Φ-baseline + beliefs."""
    return {"status": "ok", "baseline": get_reinforce_state()}

@router.post("/reinforce/reset")
async def reset_reinforce():
    """Reset reinforcement state."""
    return {"status": "ok", "baseline": reset_reinforce_state()}