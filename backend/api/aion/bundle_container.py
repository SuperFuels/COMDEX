# File: backend/api/aion/bundle_container.py

from fastapi import APIRouter
from backend.utils.bundle_builder import bundle_container  # ✅ Corrected import

router = APIRouter()

@router.get("/api/aion/bundle/{container_id}")
async def bundle(container_id: str):
    try:
        result = bundle_container(container_id)
        return {
            "status": "success",
            "container_id": container_id,
            "bundle": result
        }
    except Exception as e:
        return {
            "status": "error",
            "container_id": container_id,
            "error": str(e)
        }