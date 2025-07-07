from fastapi import APIRouter
import subprocess

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

@router.post("/run-dream", tags=["AION"])  # remove the duplicated "aion" prefix here
def run_dream_cycle():
    try:
        result = subprocess.run(
            ["python", "backend/modules/aion/dream_core.py"],
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

# No re-declaration of router here!

__all__ = ["router"]