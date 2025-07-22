# File: routes/glyphnet_router.py

from fastapi import APIRouter
from backend.modules.gip.gip_log import gip_log

router = APIRouter()

@router.get("/glyphnet/logs")
def get_glyphnet_logs():
    return {"logs": gip_log.get_logs()}