from fastapi import APIRouter

from .grid_loop import router as grid_loop_router
from .grid_tiles import router as grid_tiles_router
from . import grid_map  # if needed for side effects

router = APIRouter()
router.include_router(grid_loop_router)
router.include_router(grid_tiles_router)