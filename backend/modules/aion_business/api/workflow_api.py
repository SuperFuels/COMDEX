from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.workflows import WorkflowRunState
from backend.modules.aion_business.runtime.role_repository import RoleRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.workflows.campaign_planning import CampaignPlanningWorkflow
from backend.modules.aion_business.workflows.review_queue import ReviewQueueWorkflow
from backend.modules.aion_business.workflows.weekly_founder_review import (
    WeeklyFounderReviewWorkflow,
)

router = APIRouter(prefix="/api/aion/business/workflows", tags=["aion-business-workflows"])


class WorkflowRunRequest(BaseModel):
    workspace_id: str
    role_id: str
    days_back: int = Field(default=7, ge=1, le=365)
    include_draft: bool = True


class CampaignPlanningRunRequest(WorkflowRunRequest):
    task_id: str
    agent_id: str
    binding_id: str = "offers-binding"


def _load_workspace(workspace_id: str):
    repo = WorkspaceRepository()
    try:
        return repo.load(workspace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _load_role(workspace_id: str, role_id: str) -> RoleSpec:
    repo = RoleRepository()
    try:
        return repo.load(workspace_id, role_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/weekly-founder-review/run", response_model=WorkflowRunState)
def run_weekly_founder_review(request: WorkflowRunRequest):
    workspace = _load_workspace(request.workspace_id)
    role = _load_role(request.workspace_id, request.role_id)

    workflow = WeeklyFounderReviewWorkflow()
    return workflow.run(
        workspace=workspace,
        role=role,
        days_back=request.days_back,
        include_draft=request.include_draft,
    )


@router.post("/review-queue/run", response_model=WorkflowRunState)
def run_review_queue(request: WorkflowRunRequest):
    workspace = _load_workspace(request.workspace_id)
    role = _load_role(request.workspace_id, request.role_id)

    workflow = ReviewQueueWorkflow()
    return workflow.run(
        workspace=workspace,
        role=role,
        days_back=request.days_back,
        include_draft=request.include_draft,
    )


@router.post("/campaign-planning/run", response_model=WorkflowRunState)
def run_campaign_planning(request: CampaignPlanningRunRequest):
    from backend.modules.aion_business.runtime.agent_repository import AgentRepository
    from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository

    workspace = _load_workspace(request.workspace_id)
    role = _load_role(request.workspace_id, request.role_id)

    agent_repo = AgentRepository()
    task_repo = TaskRecordRepository()

    try:
        agent = agent_repo.load(request.workspace_id, request.agent_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        task = task_repo.load(request.workspace_id, request.task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    workflow = CampaignPlanningWorkflow()
    return workflow.run(
        workspace=workspace,
        role=role,
        task=task,
        agent=agent,
        binding_id=request.binding_id,
    )