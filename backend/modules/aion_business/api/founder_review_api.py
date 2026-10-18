from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.founder_review_trigger import (
    FounderReviewTrigger,
    FounderReviewTriggerConfig,
)


router = APIRouter(
    prefix="/api/aion/business/founder-review",
    tags=["aion-business-founder-review"],
)


def get_trigger() -> FounderReviewTrigger:
    return FounderReviewTrigger()


class FounderReviewRunRequest(BaseModel):
    workspace_id: str
    role_id: str = "ceo-core"
    days_back: int = Field(default=7, ge=1, le=365)
    include_draft: bool = True
    persist_config: bool = True
    send_email: bool = False
    send_to_emails: List[str] = Field(default_factory=list)
    from_email: Optional[str] = None


class FounderReviewConfigUpdateRequest(BaseModel):
    role_id: Optional[str] = None
    days_back: Optional[int] = Field(default=None, ge=1, le=365)
    include_draft: Optional[bool] = None
    enabled: Optional[bool] = None
    cadence: Optional[str] = None
    send_email: Optional[bool] = None
    send_to_emails: Optional[List[str]] = None
    from_email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/{workspace_id}/config", response_model=FounderReviewTriggerConfig)
def get_founder_review_config(workspace_id: str):
    trigger = get_trigger()
    try:
        return trigger.load_config(workspace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workspace_id}/config", response_model=FounderReviewTriggerConfig)
def create_or_get_founder_review_config(
    workspace_id: str,
    request: Optional[FounderReviewRunRequest] = None,
):
    trigger = get_trigger()

    req = request or FounderReviewRunRequest(workspace_id=workspace_id)

    if req.workspace_id != workspace_id:
        raise HTTPException(
            status_code=400,
            detail="workspace_id in path and body must match",
        )

    try:
        return trigger.get_or_create_config(
            workspace_id=workspace_id,
            role_id=req.role_id,
            days_back=req.days_back,
            include_draft=req.include_draft,
            enabled=True,
            send_email=req.send_email,
            send_to_emails=req.send_to_emails,
            from_email=req.from_email,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.patch("/{workspace_id}/config", response_model=FounderReviewTriggerConfig)
def update_founder_review_config(
    workspace_id: str,
    request: FounderReviewConfigUpdateRequest,
):
    trigger = get_trigger()
    try:
        return trigger.update_config(
            workspace_id=workspace_id,
            role_id=request.role_id,
            days_back=request.days_back,
            include_draft=request.include_draft,
            enabled=request.enabled,
            cadence=request.cadence,
            send_email=request.send_email,
            send_to_emails=request.send_to_emails,
            from_email=request.from_email,
            metadata=request.metadata,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.post("/run")
def run_founder_review(request: FounderReviewRunRequest):
    trigger = get_trigger()
    try:
        result = trigger.run_weekly_review(
            workspace_id=request.workspace_id,
            role_id=request.role_id,
            days_back=request.days_back,
            include_draft=request.include_draft,
            persist_config=request.persist_config,
            send_email=request.send_email,
            send_to_emails=request.send_to_emails,
            from_email=request.from_email,
        )
        return {
            "config": result.config.model_dump(mode="json"),
            "workflow_result": result.workflow_result.model_dump(mode="json"),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.post("/{workspace_id}/enable", response_model=FounderReviewTriggerConfig)
def enable_founder_review_trigger(workspace_id: str):
    trigger = get_trigger()
    try:
        return trigger.set_enabled(workspace_id=workspace_id, enabled=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workspace_id}/disable", response_model=FounderReviewTriggerConfig)
def disable_founder_review_trigger(workspace_id: str):
    trigger = get_trigger()
    try:
        return trigger.set_enabled(workspace_id=workspace_id, enabled=False)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc