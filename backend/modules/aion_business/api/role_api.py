from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.runtime.role_repository import RoleRepository


router = APIRouter(prefix="/api/aion/business/roles", tags=["aion-business-roles"])


def get_role_repository() -> RoleRepository:
    return RoleRepository()


@router.get("/{workspace_id}", response_model=List[RoleSpec])
def list_workspace_roles(
    workspace_id: str,
    role_type: Optional[str] = Query(default=None),
):
    repo = get_role_repository()
    roles = repo.list_all(workspace_id)

    if role_type:
        roles = [role for role in roles if role.role_type == role_type]

    return roles


@router.get("/{workspace_id}/{role_id}", response_model=RoleSpec)
def get_role(
    workspace_id: str,
    role_id: str,
):
    repo = get_role_repository()

    try:
        return repo.load(workspace_id, role_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc