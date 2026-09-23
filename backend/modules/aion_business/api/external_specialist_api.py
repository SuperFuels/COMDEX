from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.contracts.external_specialists import (
    ExternalSpecialistSelection,
    ExternalSpecialistSpec,
)
from backend.modules.aion_business.runtime.external_specialist_registry import (
    ExternalSpecialistRegistry,
)

router = APIRouter(
    prefix="/api/aion/business/external-specialists",
    tags=["aion-business-external-specialists"],
)


class ExternalSpecialistCreateRequest(BaseModel):
    id: str
    workspace_id: str
    name: str
    specialist_type: str
    provider: str
    action_mode: str = "api"
    capabilities: List[str] = Field(default_factory=list)
    supported_task_types: List[str] = Field(default_factory=list)
    enabled: bool = True
    priority: int = 100
    cost_class: str = "medium"
    requires_byok: bool = False
    requires_human_approval: bool = False
    metadata: dict = Field(default_factory=dict)


def get_registry() -> ExternalSpecialistRegistry:
    return ExternalSpecialistRegistry()


@router.post("", response_model=ExternalSpecialistSpec)
def create_external_specialist(request: ExternalSpecialistCreateRequest):
    registry = get_registry()
    spec = ExternalSpecialistSpec(**request.model_dump())
    registry.save(spec)
    return spec


@router.get("/{workspace_id}", response_model=List[ExternalSpecialistSpec])
def list_external_specialists(
    workspace_id: str,
    capability: Optional[str] = None,
    enabled_only: bool = True,
):
    registry = get_registry()

    if capability:
        return registry.list_by_capability(workspace_id, capability)

    if enabled_only:
        return registry.list_enabled(workspace_id)

    return registry.list_all(workspace_id)


@router.get("/{workspace_id}/{specialist_id}", response_model=ExternalSpecialistSpec)
def get_external_specialist(workspace_id: str, specialist_id: str):
    registry = get_registry()
    try:
        return registry.load(workspace_id, specialist_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{workspace_id}/resolve/{capability}", response_model=ExternalSpecialistSelection)
def resolve_external_specialist(workspace_id: str, capability: str):
    registry = get_registry()
    return registry.resolve_for_capability(
        workspace_id=workspace_id,
        capability=capability,
    )