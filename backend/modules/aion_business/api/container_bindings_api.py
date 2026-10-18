from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.modules.aion_business.runtime.business_container_service import (
    BusinessContainerService,
)
from backend.modules.aion_business.runtime.container_binding_repository import (
    ContainerBindingRepository,
)


router = APIRouter(
    prefix="/api/aion/business/container-bindings",
    tags=["aion-business-container-bindings"],
)


def get_repository() -> ContainerBindingRepository:
    return ContainerBindingRepository()


def get_service() -> BusinessContainerService:
    return BusinessContainerService()


@router.get("/{workspace_id}")
def list_container_bindings(workspace_id: str) -> Dict[str, Any]:
    try:
        service = get_service()
        service.ensure_canonical_containers(workspace_id)

        repository = get_repository()
        items = [
            item.model_dump(mode="json")
            for item in repository.list_bindings(workspace_id)
        ]
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "items": items,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc