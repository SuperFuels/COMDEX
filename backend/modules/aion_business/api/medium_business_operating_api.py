"""Local Boardroom surface for multi-entity, project and delegated authority operations."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.medium_business_operating_service import MediumBusinessOperatingService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


router = APIRouter(prefix="/api/aion/business/medium", tags=["aion-medium-business"])


class ConfigureRequest(BaseModel):
    model: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = None
    changed_by: str = Field(min_length=1, max_length=200)


class AccessRequest(BaseModel):
    person_id: str
    capability: str
    entity_id: str = ""
    unit_id: str = ""
    location_id: str = ""
    project_id: str = ""
    amount: float | None = None
    action_history: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    requester_id: str
    approver_id: str
    amount: float = Field(ge=0)
    action_history: list[dict[str, Any]] = Field(default_factory=list)


def _service(value: str) -> tuple[str, MediumBusinessOperatingService]:
    workspace_id = canonical_business_id(value)
    if not workspace_id:
        raise HTTPException(status_code=400, detail="registered_business_id_required")
    root = AIONBusinessPaths.business_container_dir(workspace_id) / "medium_business"
    return workspace_id, MediumBusinessOperatingService(root)


@router.get("/{workspace_id}")
def state(workspace_id: str) -> dict[str, Any]:
    key, service = _service(workspace_id)
    return {"ok": True, "workspace_id": key, "model": service.state()}


@router.put("/{workspace_id}")
def configure(workspace_id: str, request: ConfigureRequest) -> dict[str, Any]:
    key, service = _service(workspace_id)
    try:
        model = service.configure(request.model, expected_revision=request.expected_revision, changed_by=request.changed_by)
    except ValueError as error:
        code = str(error)
        raise HTTPException(status_code=409 if "revision_conflict" in code else 422, detail=code) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/access-decision")
def access_decision(workspace_id: str, request: AccessRequest) -> dict[str, Any]:
    key, service = _service(workspace_id)
    return {"ok": True, "workspace_id": key, "decision": service.access_decision(**request.model_dump())}


@router.post("/{workspace_id}/workflows/{workflow_id}/decision")
def workflow_decision(workspace_id: str, workflow_id: str, request: WorkflowRequest) -> dict[str, Any]:
    key, service = _service(workspace_id)
    return {"ok": True, "workspace_id": key, "decision": service.workflow_decision(workflow_id=workflow_id, **request.model_dump())}


@router.get("/{workspace_id}/portfolio/{person_id}")
def portfolio(workspace_id: str, person_id: str) -> dict[str, Any]:
    key, service = _service(workspace_id)
    try:
        result = service.portfolio_dashboard(viewer_id=person_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"ok": True, "workspace_id": key, "portfolio": result}


@router.get("/{workspace_id}/workspace/{person_id}")
def bounded_workspace(workspace_id: str, person_id: str) -> dict[str, Any]:
    key, service = _service(workspace_id)
    return {"ok": True, "workspace_id": key, "workspace": service.workspace_projection(person_id=person_id)}


@router.get("/{workspace_id}/support-bundle/{person_id}")
def support_bundle(workspace_id: str, person_id: str) -> dict[str, Any]:
    key, service = _service(workspace_id)
    try:
        bundle = service.support_bundle(viewer_id=person_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"ok": True, "workspace_id": key, "bundle": bundle}


@router.get("/{workspace_id}/audit-export/{person_id}")
def audit_export(workspace_id: str, person_id: str) -> dict[str, Any]:
    key, service = _service(workspace_id)
    try:
        export = service.audit_export(viewer_id=person_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"ok": True, "workspace_id": key, "export": export}
