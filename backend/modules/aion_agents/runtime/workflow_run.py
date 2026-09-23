from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


WorkflowRunStatus = Literal[
    "queued",
    "running",
    "waiting_approval",
    "blocked",
    "completed",
    "failed",
    "cancelled",
]

WorkflowStepRunStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
    "waiting_approval",
]


class WorkflowStepRun(BaseModel):
    step_id: str
    step_name: str
    step_kind: str
    status: WorkflowStepRunStatus = "pending"
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class WorkflowRun(BaseModel):
    id: str
    workspace_id: str
    workflow_id: str
    workflow_version: int = 1
    workflow_name: Optional[str] = None
    agent_id: Optional[str] = None
    department_key: Optional[str] = None
    trigger_id: Optional[str] = None
    trigger_event_type: Optional[str] = None
    status: WorkflowRunStatus = "queued"
    current_step_id: Optional[str] = None
    approval_request_id: Optional[str] = None
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    result_payload: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    step_runs: List[WorkflowStepRun] = Field(default_factory=list)
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None