from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.business_container_service import (
    BusinessContainerService,
)
from backend.modules.aion_business.runtime.boardroom_conversation_service import (
    BoardroomConversationService,
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


class BoardroomConversationRequest(BaseModel):
    team_mode: str = Field(default="board", max_length=80)
    seat_key: str = Field(default="aion", max_length=80)
    messages: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    expected_revision: int | None = Field(default=None, ge=0)


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


@router.get("/{workspace_id}/conversations/{team_mode}/{seat_key}")
def get_boardroom_conversation(
    workspace_id: str, team_mode: str, seat_key: str,
) -> Dict[str, Any]:
    try:
        return BoardroomConversationService().load(
            workspace_id, team_mode=team_mode, seat_key=seat_key,
        )
    except RuntimeError as exc:
        if str(exc) == "business_vault_unavailable":
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        raise


@router.put("/{workspace_id}/conversations")
def save_boardroom_conversation(
    workspace_id: str, request: BoardroomConversationRequest,
) -> Dict[str, Any]:
    try:
        return BoardroomConversationService().save(
            workspace_id, team_mode=request.team_mode, seat_key=request.seat_key,
            messages=request.messages, expected_revision=request.expected_revision,
        )
    except RuntimeError as exc:
        if str(exc) == "business_vault_unavailable":
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        raise
    except ValueError as exc:
        if str(exc) == "boardroom_conversation_revision_conflict":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
