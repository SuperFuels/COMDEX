from fastapi import APIRouter
from modules.sim.grid_engine import GridWorld

import base64
from io import BytesIO

router = APIRouter()

@router.get("/aion/grid/map")
def get_grid_map():
    grid = GridWorld()
    image = grid.render_tile_map()

    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {"image_base64": image_base64}
