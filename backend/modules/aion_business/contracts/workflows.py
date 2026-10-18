from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


WorkflowTrigger = Literal["manual", "scheduled", "event"]
WorkflowStateModel = Literal["stateless", "resumable"]
WorkflowRunStatus = Literal["queued", "running", "blocked", "completed", "failed", "cancelled"]

WorkflowStepType = Literal[
    "retrieval",
    "planning",
    "task_agent_spawn",
    "skill_execution",
    "external_work_order",
    "review",
    "notification",
    "persistence",
]


class WorkflowStep(BaseModel):
    id: str
    step_type: WorkflowStepType
    name: str

    description: Optional[str] = None
    enabled: bool = True

    config: Dict[str, Any] = Field(default_factory=dict)
    success_criteria: List[str] = Field(default_factory=list)

    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    requires_approval: bool = False


class WorkflowSpec(BaseModel):
    id: str
    workspace_id: str
    name: str
    owner_role: str

    trigger: WorkflowTrigger = "manual"
    steps: List[WorkflowStep] = Field(default_factory=list)

    success_criteria: List[str] = Field(default_factory=list)
    escalation_policy_ref: Optional[str] = None
    state_model: WorkflowStateModel = "stateless"

    enabled: bool = True
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class WorkflowRunState(BaseModel):
    id: str
    workflow_id: str
    workspace_id: str

    status: WorkflowRunStatus = "queued"
    current_step_id: Optional[str] = None
    completed_step_ids: List[str] = Field(default_factory=list)
    failed_step_id: Optional[str] = None

    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)

    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)