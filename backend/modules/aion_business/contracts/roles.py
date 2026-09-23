from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


RoleType = Literal["CEO", "COO", "CTO", "CMO", "SUPPORT", "RESEARCH", "FINANCE", "CUSTOM"]


class RoleSpec(BaseModel):
    id: str
    workspace_id: str
    role_type: RoleType
    business_type: str
    objective_set: List[str] = Field(default_factory=list)
    allowed_container_ids: List[str] = Field(default_factory=list)
    allowed_skill_ids: List[str] = Field(default_factory=list)
    spawn_policy_ref: Optional[str] = None
    escalation_policy_ref: Optional[str] = None
    model_policy_ref: Optional[str] = None
    memory_scope: Literal["role"] = "role"
    persistence: Literal["persistent"] = "persistent"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)