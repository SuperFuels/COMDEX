# backend/api/aion/__init__.py

from fastapi import APIRouter

from .grid_loop import router as grid_loop_router
from .grid_tiles import router as grid_tiles_router
from . import grid_map  # if needed for side effects

from backend.api.aion.container_api import router as container_router

router = APIRouter()

# Include all routers
router.include_router(grid_loop_router)
router.include_router(grid_tiles_router)
router.include_router(container_router, prefix="")  # mounts at /api/aion/...