from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


AuditEventType = Literal[
    "agent_transition",
    "workflow_completed",
    "workflow_failed",
    "task_created",
    "task_completed",
    "task_failed",
    "provider_call",
    "memory_access",
    "skill_run",
    "custom",
]

TraceEventType = Literal[
    "agent_trace",
    "workflow_trace",
    "skill_trace",
    "system_trace",
]

MemoryAction = Literal["read", "write"]
ProviderCapability = Literal[
    "drafting",
    "rewrite",
    "summarization",
    "analysis",
    "reasoning",
    "planning",
    "classification",
]


class AuditEvent(BaseModel):
    id: str
    workspace_id: str
    event_type: AuditEventType | str

    role_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    workflow_id: Optional[str] = None

    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)


class TraceEvent(BaseModel):
    id: str
    workspace_id: str
    trace_type: TraceEventType | str

    role_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    workflow_id: Optional[str] = None

    stage: Optional[str] = None
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)

    created_at: str = Field(default_factory=utc_now_iso)


class MemoryAccessEvent(BaseModel):
    id: str
    workspace_id: str
    binding_id: str

    action: MemoryAction | str
    allowed: bool
    reason: str
    scope: Optional[str] = None

    role_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class ProviderCallEvent(BaseModel):
    id: str
    workspace_id: str

    provider: str
    capability: Optional[ProviderCapability | str] = None

    actor_id: Optional[str] = None
    role_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    workflow_id: Optional[str] = None
    workflow_run_id: Optional[str] = None

    model_policy_ref: Optional[str] = None
    model: Optional[str] = None

    request_summary: str
    response_summary: Optional[str] = None
    prompt_preview: Optional[str] = None

    success: bool
    error_code: Optional[str] = None

    usage: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    fallback_used: bool = False
    cost_estimate: float = 0.0

    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)