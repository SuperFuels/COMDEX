# backend/routes/wormholes.py
from fastapi import APIRouter, Query
from backend.modules.teleport.wormhole_resolver import resolve_wormhole

router = APIRouter(prefix="/api/wormhole", tags=["wormholes"])

@router.get("/resolve")
def api_resolve(name: str = Query(..., min_length=1)):
    return resolve_wormhole(name)