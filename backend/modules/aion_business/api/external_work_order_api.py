from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.contracts.external_work_orders import (
    ExternalWorkOrderRecord,
)
from backend.modules.aion_business.runtime.external_work_order_manager import (
    ExternalWorkOrderManager,
)
from backend.modules.aion_business.runtime.external_work_order_repository import (
    ExternalWorkOrderRepository,
)

router = APIRouter(
    prefix="/api/aion/business/external-work-orders",
    tags=["aion-business-external-work-orders"],
)


class ExternalWorkOrderCreateRequest(BaseModel):
    workspace_id: str
    capability: str
    objective: str
    parent_task_id: Optional[str] = None
    priority: str = "medium"
    inputs: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class ExternalWorkOrderCompleteRequest(BaseModel):
    outputs: dict = Field(default_factory=dict)


class ExternalWorkOrderFailRequest(BaseModel):
    error_code: str


def get_repository() -> ExternalWorkOrderRepository:
    return ExternalWorkOrderRepository()


def get_manager() -> ExternalWorkOrderManager:
    return ExternalWorkOrderManager()


@router.post("", response_model=ExternalWorkOrderRecord)
def create_external_work_order(request: ExternalWorkOrderCreateRequest):
    manager = get_manager()
    return manager.create_work_order(
        workspace_id=request.workspace_id,
        capability=request.capability,
        objective=request.objective,
        parent_task_id=request.parent_task_id,
        inputs=request.inputs,
        priority=request.priority,
        metadata=request.metadata,
    )


@router.get("/{workspace_id}", response_model=List[ExternalWorkOrderRecord])
def list_external_work_orders(
    workspace_id: str,
    status: Optional[str] = None,
):
    repo = get_repository()
    records = repo.list_all(workspace_id)
    if status:
        records = [record for record in records if record.status == status]
    return records


@router.get("/{workspace_id}/{work_order_id}", response_model=ExternalWorkOrderRecord)
def get_external_work_order(workspace_id: str, work_order_id: str):
    repo = get_repository()
    try:
        return repo.load(workspace_id, work_order_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workspace_id}/{work_order_id}/dispatch", response_model=ExternalWorkOrderRecord)
def dispatch_external_work_order(workspace_id: str, work_order_id: str):
    manager = get_manager()
    try:
        return manager.dispatch(workspace_id, work_order_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workspace_id}/{work_order_id}/complete", response_model=ExternalWorkOrderRecord)
def complete_external_work_order(
    workspace_id: str,
    work_order_id: str,
    request: ExternalWorkOrderCompleteRequest,
):
    manager = get_manager()
    try:
        return manager.complete(
            workspace_id,
            work_order_id,
            outputs=request.outputs,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{workspace_id}/{work_order_id}/fail", response_model=ExternalWorkOrderRecord)
def fail_external_work_order(
    workspace_id: str,
    work_order_id: str,
    request: ExternalWorkOrderFailRequest,
):
    manager = get_manager()
    try:
        return manager.fail(
            workspace_id,
            work_order_id,
            error_code=request.error_code,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc