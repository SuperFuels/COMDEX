# ===============================
# 📁 backend/api/api_qfc_extras.py
# ===============================
from typing import Optional, Dict, Any, Literal
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api", tags=["qfc-extras"])
security = HTTPBearer(auto_error=False)


def _validate(creds: Optional[HTTPAuthorizationCredentials]) -> None:
    """
    If a Bearer token is provided, require it to match 'valid_token'.
    Token is optional so local/dev calls without auth still work.
    """
    if creds and creds.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/qfc_entanglement")
async def qfc_entanglement(
    cell_id: str = Query(..., description="Origin cell id"),
    file: Optional[str] = Query(None, description="Sheet file path (.atom / .sqs.json)"),
    container_id: Optional[str] = Query(None, description="QFC container id"),
    direction: Literal["forward", "reverse"] = Query("forward", description="LightCone direction"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Minimal stub so the HUD never 404s.
    Returns an **empty** list of 'updates' you can populate later with real
    entanglement/prediction-fork events.

    Response shape is stable and backward-compatible with earlier stub
    (it still includes `updates: []`), while also echoing inputs for debugging.
    """
    _validate(credentials)

    return {
        "cell_id": cell_id,
        "file": file,
        "container_id": container_id,
        "direction": direction,
        "updates": [],   # <- fill later with real events
        "count": 0,      # convenience field for HUD counters
    }


@router.get("/qfc_entangled")
async def qfc_entangled(
    cell_id: str = Query(..., description="Origin cell id"),
    container_id: Optional[str] = Query(None, description="QFC container id"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Secondary stub used by some HUD variants.
    Also returns an empty 'updates' list for now.
    """
    _validate(credentials)

    return {
        "cell_id": cell_id,
        "container_id": container_id,
        "updates": [],  # <- fill later with summarized entanglements
        "count": 0,
    }