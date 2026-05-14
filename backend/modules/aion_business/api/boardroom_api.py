from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.business_container_service import (
    BusinessContainerService,
)

router = APIRouter(
    prefix="/api/aion/business/boardroom",
    tags=["aion-business-boardroom"],
)


def get_business_container_service() -> BusinessContainerService:
    return BusinessContainerService()


class BoardroomFrameRequest(BaseModel):
    workspace_id: str
    active_zone: str = Field(default="coo")
    selected_seat_id: Optional[str] = None


class BoardroomExistsResponse(BaseModel):
    workspace_id: str
    exists: bool
    source: str = "containers"


def _load_canonical_boardroom(
    workspace_id: str,
    *,
    active_zone: str = "coo",
    selected_seat_id: Optional[str] = None,
) -> Dict[str, Any]:
    service = get_business_container_service()

    try:
        service.ensure_canonical_containers(workspace_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ensure canonical containers: {type(exc).__name__}: {exc}",
        ) from exc

    try:
        payload = service.get_boardroom_payload(
            workspace_id,
            active_zone=active_zone,
            selected_seat_id=selected_seat_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Canonical boardroom not found for workspace: {workspace_id}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load canonical boardroom: {type(exc).__name__}: {exc}",
        ) from exc

    if not isinstance(payload, dict) or not payload:
        raise HTTPException(
            status_code=404,
            detail=f"Canonical boardroom not found for workspace: {workspace_id}",
        )

    payload = dict(payload)
    payload.setdefault("workspace_id", workspace_id)
    payload["active_zone"] = active_zone or payload.get("active_zone") or "coo"
    payload["selected_seat_id"] = (
        selected_seat_id
        if selected_seat_id is not None
        else payload.get("selected_seat_id")
    )
    return payload


@router.get("/{workspace_id}")
def get_boardroom_frame(
    workspace_id: str,
    active_zone: str = "coo",
    selected_seat_id: Optional[str] = None,
) -> Dict[str, Any]:
    return _load_canonical_boardroom(
        workspace_id,
        active_zone=active_zone,
        selected_seat_id=selected_seat_id,
    )


@router.post("/frame")
def create_boardroom_frame(request: BoardroomFrameRequest) -> Dict[str, Any]:
    return _load_canonical_boardroom(
        request.workspace_id,
        active_zone=request.active_zone,
        selected_seat_id=request.selected_seat_id,
    )


@router.get("/{workspace_id}/exists", response_model=BoardroomExistsResponse)
def boardroom_exists(workspace_id: str) -> BoardroomExistsResponse:
    service = get_business_container_service()

    try:
        service.ensure_canonical_containers(workspace_id)
        payload = service.get_boardroom_payload(workspace_id)
    except Exception:
        payload = None

    return BoardroomExistsResponse(
        workspace_id=workspace_id,
        exists=isinstance(payload, dict) and bool(payload),
        source="containers",
    )