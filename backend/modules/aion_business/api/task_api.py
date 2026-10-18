from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository


router = APIRouter(prefix="/api/aion/business/tasks", tags=["aion-business-tasks"])


def get_task_repository() -> TaskRecordRepository:
    return TaskRecordRepository()


@router.get("/{workspace_id}", response_model=List[TaskRecord])
def list_workspace_tasks(
    workspace_id: str,
    status: Optional[str] = None,
    owned_by_role: Optional[str] = None,
):
    repo = get_task_repository()
    tasks = repo.list_for_workspace(workspace_id)

    if status:
        tasks = [task for task in tasks if task.status == status]

    if owned_by_role:
        tasks = [task for task in tasks if task.owned_by_role == owned_by_role]

    return tasks


@router.get("/{workspace_id}/escalated", response_model=List[TaskRecord])
def list_escalated_tasks(
    workspace_id: str,
):
    repo = get_task_repository()
    tasks = repo.list_for_workspace(workspace_id)
    return [task for task in tasks if task.status == "escalated"]


@router.get("/{workspace_id}/{task_id}", response_model=TaskRecord)
def get_task(
    workspace_id: str,
    task_id: str,
):
    repo = get_task_repository()

    try:
        return repo.load(workspace_id, task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc