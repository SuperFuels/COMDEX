"""HTTP surface for the HR Pilot organisation and authority workspace."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.organization_authority_service import (
    OrganizationAuthorityService,
    ROLE_TEMPLATES,
    standard_departments,
)


router = APIRouter(prefix="/api/aion/business/organisation", tags=["aion-business-organisation"])


class OrganizationSaveRequest(BaseModel):
    model: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = None
    changed_by: str = "current_user"


class AccessDecisionRequest(BaseModel):
    person_id: str
    capability: str
    department_id: str | None = None
    amount: float | None = None
    subject_person_id: str | None = None


def _workspace(value: str) -> str:
    workspace_id = canonical_business_id(value)
    if not workspace_id:
        raise HTTPException(status_code=400, detail="registered_business_id_required")
    return workspace_id


@router.get("/templates")
def organization_templates() -> dict[str, Any]:
    return {
        "ok": True,
        "role_templates": ROLE_TEMPLATES,
        "standard_departments": standard_departments(),
        "employment_types": [
            {"id": "owner", "name": "Owner / director"},
            {"id": "employee", "name": "Employee"},
            {"id": "self_employed", "name": "Self-employed person"},
            {"id": "contractor", "name": "Contractor"},
            {"id": "freelancer", "name": "Freelancer"},
            {"id": "external_adviser", "name": "External adviser / accountant"},
        ],
    }


@router.get("/{workspace_id}")
def get_organization(workspace_id: str) -> dict[str, Any]:
    key = _workspace(workspace_id)
    return {"ok": True, "workspace_id": key, "model": OrganizationAuthorityService().get(key)}


@router.put("/{workspace_id}")
def save_organization(workspace_id: str, request: OrganizationSaveRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        model = OrganizationAuthorityService().save(
            key, request.model, expected_revision=request.expected_revision, changed_by=request.changed_by,
        )
    except ValueError as error:
        code = str(error)
        status = 409 if code == "organization_revision_conflict" else 422
        raise HTTPException(status_code=status, detail=code) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/access-decision")
def access_decision(workspace_id: str, request: AccessDecisionRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    decision = OrganizationAuthorityService().access_decision(
        key, person_id=request.person_id, capability=request.capability,
        department_id=request.department_id, amount=request.amount,
        subject_person_id=request.subject_person_id,
    )
    return {"ok": True, "workspace_id": key, "decision": decision}


@router.get("/{workspace_id}/viewer-projection/{person_id}")
def viewer_projection(workspace_id: str, person_id: str) -> dict[str, Any]:
    key = _workspace(workspace_id)
    projection = OrganizationAuthorityService().viewer_projection(key, person_id=person_id)
    return {"ok": True, "workspace_id": key, "projection": projection}
