# backend/api/aion/grid_tiles.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/aion/grid/tiles")
def get_grid_tiles():
    return {"message": "🔲 Grid tiles endpoint ready."}