from fastapi import APIRouter
import subprocess

router = APIRouter()

@router.post("/aion/run-dream", tags=["AION"])
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
router = APIRouter()

# your route definitions here...

# expose it at the bottom
__all__ = ["router"]