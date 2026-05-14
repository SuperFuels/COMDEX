from fastapi import APIRouter, HTTPException
from typing import List
from backend.modules.runtime.container_runtime import get_all_containers  # Adjust if different
from backend.modules.models.container_model import ContainerModel  # Replace with your actual container schema/model

router = APIRouter()

@router.get("/api/aion/containers/zone/{zone_id}", response_model=List[ContainerModel])
async def get_containers_by_zone(zone_id: str):
    """
    ✅ Return only containers belonging to a specific zone.
    Used by the Multiverse Warp Drive Navigator to reduce map clutter.
    """
    try:
        all_containers = await get_all_containers()  # or sync call depending on implementation

        zone_containers = [
            c for c in all_containers if not getattr(c, "region", None) or getattr(c, "region", None) == zone_id
        ]

        return zone_containers

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch containers for zone {zone_id}: {str(e)}")