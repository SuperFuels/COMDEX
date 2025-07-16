from fastapi import APIRouter, Query
from backend.modules.dimensions.time_controller import TimeController

router = APIRouter()
time_controller = TimeController()

@router.get("/api/aion/container_tick")
def get_container_tick(container_id: str = Query(...)):
    tick = time_controller.get_tick(container_id)
    return {"container_id": container_id, "tick": tick}
    