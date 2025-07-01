from fastapi import APIRouter
from modules.sim.grid_engine import GridWorld

router = APIRouter()

@router.get("/aion/grid-progress")
def get_grid_progress():
    engine = GridWorld()
    stats = engine.get_progress()
    return stats