from fastapi import APIRouter
from pathlib import Path
import json

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

GRID_STATE_PATH = Path("backend/modules/aion/grid_world_state.json")

@router.get("/api/aion/grid-progress", tags=["AION"])
def get_grid_progress():
    if not GRID_STATE_PATH.exists():
        return {"completion": 0, "message": "No grid progress yet."}
    try:
        with open(GRID_STATE_PATH, "r") as f:
            state = json.load(f)
            percent = state.get("completion", 0)
            return {"completion": percent, "message": state.get("status", "Running")}
    except Exception as e:
        return {"completion": 0, "message": f"Error reading state: {e}"}
