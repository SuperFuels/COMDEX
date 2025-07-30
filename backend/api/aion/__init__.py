# backend/api/aion/__init__.py

from fastapi import APIRouter
from backend.main import app  # ✅ Ensure 'app' is imported if not already

from .grid_loop import router as grid_loop_router
from .grid_tiles import router as grid_tiles_router
from . import grid_map  # if needed for side effects

from backend.api.aion.container_api import router as container_router
from .engine_qwave import router as qwave_router  # ✅ QWave Engine router

# Create a central API router
router = APIRouter()

# Include all routers
router.include_router(grid_loop_router)
router.include_router(grid_tiles_router)
router.include_router(container_router, prefix="")  # mounts at /api/aion/...

# ✅ Mount QWave Engine routes
app.include_router(qwave_router, prefix="/api/aion", tags=["QWave Engine"])