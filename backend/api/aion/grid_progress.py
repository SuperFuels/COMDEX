from fastapi import APIRouter
from backend.modules.sim.grid_engine import GridWorld

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

@router.get("/aion/grid-progress")
def get_grid_progress():
    engine = GridWorld()
    stats = engine.get_progress()
    return stats