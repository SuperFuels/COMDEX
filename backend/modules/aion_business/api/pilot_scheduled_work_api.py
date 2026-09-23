from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.pilot_scheduled_work_service import PilotScheduledWorkService


router = APIRouter(prefix="/api/aion/pilot/scheduled-work", tags=["aion-pilot-scheduled-work"])
service = PilotScheduledWorkService()


class PilotScheduleCreateRequest(BaseModel):
    title: str
    job_type: str
    cadence_minutes: int = Field(ge=5, le=43_200)
    created_by_person_id: str
    prompt: str = ""
    query: str | None = None
    max_results: int = Field(default=10, ge=1, le=25)
    enabled: bool = False
    action_policy: str = "approval_required"


class PilotScheduleEnabledRequest(BaseModel):
    enabled: bool
    changed_by_person_id: str


def _workspace(candidate: str) -> str:
    return canonical_business_id(candidate) or candidate


def _call(function, *args, **kwargs) -> Any:
    try:
        return function(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{workspace_id}")
def list_pilot_scheduled_work(workspace_id: str) -> dict[str, Any]:
    return _call(service.list, _workspace(workspace_id))


@router.post("/{workspace_id}")
def create_pilot_scheduled_work(workspace_id: str, request: PilotScheduleCreateRequest) -> dict[str, Any]:
    return _call(service.create, _workspace(workspace_id), **request.model_dump())


@router.post("/{workspace_id}/{schedule_id}/enabled")
def set_pilot_scheduled_work_enabled(workspace_id: str, schedule_id: str,
                                     request: PilotScheduleEnabledRequest) -> dict[str, Any]:
    return _call(service.set_enabled, _workspace(workspace_id), schedule_id,
                 enabled=request.enabled, changed_by_person_id=request.changed_by_person_id)


@router.post("/{workspace_id}/{schedule_id}/run")
def run_pilot_scheduled_work(workspace_id: str, schedule_id: str) -> dict[str, Any]:
    return _call(service.run, _workspace(workspace_id), schedule_id)
