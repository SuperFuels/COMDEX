from fastapi import APIRouter
from backend.modules.sim.grid_engine import GridWorld

import base64
from io import BytesIO

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

@router.get("/aion/grid/map")
def get_grid_map():
    grid = GridWorld()
    image = grid.render_tile_map()

    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {"image_base64": image_base64}
