from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)

router = APIRouter(
    prefix="/api/aion/business/workflow-file-cabinet",
    tags=["aion-business-workflow-file-cabinet"],
)


@router.get("/{workspace_id}")
def get_workflow_file_cabinet(workspace_id: str) -> Dict[str, Any]:
    try:
        return WorkflowFileCabinetRepository.load(workspace_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workspace_id}")
def save_workflow_file_cabinet(workspace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return WorkflowFileCabinetRepository.save(workspace_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
