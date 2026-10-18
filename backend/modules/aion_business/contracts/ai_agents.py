from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


AIAgentStatus = Literal["draft", "active", "inactive"]


class AIAgentSpec(BaseModel):
    id: str
    workspace_id: str

    name: str
    agent_type: str
    department_key: str

    role_id: Optional[str] = None
    model_policy_ref: Optional[str] = None

    status: AIAgentStatus = "draft"
    active: bool = True

    team_ids: List[str] = Field(default_factory=list)
    function_ids: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)

    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "AIAgentSpec":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return AIAgentSpec(**data)