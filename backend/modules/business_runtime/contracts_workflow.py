from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WorkflowStepKind(str, Enum):
    CREATE_BRIEF = "create_brief"
    DRAFT_CAPTION = "draft_caption"
    DRAFT_CAROUSEL = "draft_carousel"
    ATTACH_CONNECTOR_CONTEXT = "attach_connector_context"
    REQUEST_APPROVAL = "request_approval"
    COMPLETE_RUN = "complete_run"


class WorkflowRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowExecutionMode(str, Enum):
    DRAFT_ONLY = "draft_only"
    DRAFT_AND_APPROVAL = "draft_and_approval"
    AUTONOMOUS = "autonomous"


@dataclass(slots=True)
class WorkflowStepDefinition:
    id: str
    label: str
    kind: WorkflowStepKind
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowDefinition:
    id: str
    name: str
    department_key: str
    operator_id: str
    version: str
    execution_mode: WorkflowExecutionMode
    steps: List[WorkflowStepDefinition]
    is_active: bool = True
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class WorkflowStepRun:
    id: str
    step_id: str
    kind: str
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass(slots=True)
class WorkflowRun:
    id: str
    workflow_id: str
    workflow_name: str
    operator_id: str
    department_key: str
    trigger_kind: str
    execution_mode: WorkflowExecutionMode
    status: WorkflowRunStatus = WorkflowRunStatus.QUEUED
    current_step_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    step_runs: List[WorkflowStepRun] = field(default_factory=list)
    approval_request_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None

    def touch(self) -> None:
        self.updated_at = utc_now_iso()