from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


TaskStatus = Literal["queued", "running", "blocked", "completed", "failed", "escalated"]
TaskPriority = Literal["low", "medium", "high", "critical"]


class ExternalWorkOrder(BaseModel):
    id: str
    parent_task_id: str
    provider: str
    capability: str
    objective: str
    business_context: Dict[str, Any] = Field(default_factory=dict)
    task_context: Dict[str, Any] = Field(default_factory=dict)
    allowed_tools: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    budget_limit: float = 0.0
    output_contract: Optional[str] = None
    trace_required: bool = True
    escalation_policy: Optional[str] = None


class TaskRecord(BaseModel):
    id: str
    workspace_id: str
    created_by: str
    owned_by_role: str
    assigned_agent_id: Optional[str] = None
    objective: str

    status: TaskStatus = "queued"
    priority: TaskPriority = "medium"

    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)

    linked_containers: List[str] = Field(default_factory=list)
    linked_work_orders: List[str] = Field(default_factory=list)

    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class LearningRecord(BaseModel):
    id: str
    source_type: Literal["task", "workflow", "user_feedback", "outcome_review"]
    source_id: str
    business_area: str
    signal_type: Literal["success", "failure", "preference", "weakness", "routing_hint"]
    summary: str
    confidence: float = 0.0
    writable_influence: bool = False
    created_at: str = Field(default_factory=utc_now_iso)