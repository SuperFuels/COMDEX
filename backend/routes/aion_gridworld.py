# 📁 backend/routes/aion_gridworld.py
from fastapi import APIRouter
import subprocess

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

@router.post("/aion/grid-world", tags=["AION"])
def run_grid_world():
    try:
        result = subprocess.run(
            ["python", "backend/modules/aion/grid_world.py"],
            capture_output=True,
            text=True,
        )
        return {
            "status": "ok",
            "output": result.stdout
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
        router = APIRouter()

# ... your endpoints ...

__all__ = ["router"]