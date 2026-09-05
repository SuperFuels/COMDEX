from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.services.aion_mission_mode.boardroom_session_artifacts import (
    commit_boardroom_session_artifact,
    create_file_cabinet_pointer_for_boardroom_session,
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


@router.post("/{workspace_id}/boardroom-sessions")
def save_boardroom_session_artifact(workspace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the complete Board meeting packet before publishing its cabinet pointer."""
    try:
        safe_workspace_id = WorkflowFileCabinetRepository._safe_id(workspace_id)
        business_id = WorkflowFileCabinetRepository._safe_id(str(payload.get("business_id") or ""))
        session_id = str(payload.get("session_id") or "").strip()
        session_type = str(payload.get("session_type") or "business_assessment").strip()

        if not session_id:
            raise ValueError("session_id_required")
        if business_id != safe_workspace_id:
            raise ValueError("boardroom_workspace_business_mismatch")

        record = commit_boardroom_session_artifact(
            business_id=business_id,
            session_id=session_id,
            session_type=session_type,
            full_session_payload=payload,
            platform_root=AIONBusinessPaths.ROOT,
        )
        return {
            "ok": True,
            "record": record,
            "pointer": create_file_cabinet_pointer_for_boardroom_session(record),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{workspace_id}/items/{item_id}/preview")
def preview_workflow_file_cabinet_item(workspace_id: str, item_id: str) -> Dict[str, Any]:
    try:
        return WorkflowFileCabinetRepository.preview(workspace_id, item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
