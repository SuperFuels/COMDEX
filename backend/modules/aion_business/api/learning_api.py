from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.modules.aion_business.contracts.tasks import LearningRecord
from backend.modules.aion_business.runtime.learning_service import LearningService


router = APIRouter(prefix="/api/aion/business/learning", tags=["aion-business-learning"])


def get_learning_service() -> LearningService:
    return LearningService()


@router.get("/{workspace_id}", response_model=List[LearningRecord])
def list_workspace_learning(
    workspace_id: str,
    signal_type: Optional[str] = None,
    business_area: Optional[str] = None,
    source_type: Optional[str] = None,
):
    service = get_learning_service()

    if signal_type:
        return service.list_by_signal_type(
            workspace_id=workspace_id,
            signal_type=signal_type,
        )

    if business_area:
        return service.list_by_business_area(
            workspace_id=workspace_id,
            business_area=business_area,
        )

    if source_type:
        return service.list_by_source_type(
            workspace_id=workspace_id,
            source_type=source_type,
        )

    return service.list_workspace_learning(workspace_id=workspace_id)


@router.get("/{workspace_id}/query", response_model=List[LearningRecord])
def query_workspace_learning(
    workspace_id: str,
    signal_type: Optional[str] = Query(default=None),
    business_area: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
):
    return list_workspace_learning(
        workspace_id=workspace_id,
        signal_type=signal_type,
        business_area=business_area,
        source_type=source_type,
    )


@router.get("/{workspace_id}/{record_id}", response_model=LearningRecord)
def get_learning_record(
    workspace_id: str,
    record_id: str,
):
    service = get_learning_service()

    try:
        return service.load_record(
            workspace_id=workspace_id,
            record_id=record_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc