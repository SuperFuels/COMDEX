from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


AgentType = Literal["persistent_role", "task", "workflow"]
MemoryScope = Literal["none", "task", "workflow", "role", "workspace"]
AgentTrigger = Literal["manual", "event", "scheduled", "delegated"]
AgentLifecycleState = Literal[
    "defined",
    "eligible",
    "spawned",
    "initialized",
    "running",
    "blocked",
    "completed",
    "failed",
    "escalated",
    "terminated",
]


class AgentSpec(BaseModel):
    id: str
    workspace_id: str

    agent_type: AgentType
    role: str
    parent_role_id: Optional[str] = None
    business_type: str
    objective: str

    allowed_skills: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    allowed_containers: List[str] = Field(default_factory=list)

    memory_scope: MemoryScope = "task"
    output_contract: Optional[str] = None
    trigger: AgentTrigger = "delegated"
    escalation_rules: List[str] = Field(default_factory=list)

    cost_budget: float = 0.0
    model_policy_ref: Optional[str] = None
    ttl_seconds: int = 3600
    writable: bool = False

    lifecycle_state: AgentLifecycleState = "defined"
    assigned_task_id: Optional[str] = None

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)