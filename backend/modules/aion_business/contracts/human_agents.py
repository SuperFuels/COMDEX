from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


HumanAgentStatus = Literal["draft", "active", "inactive"]


class HumanAgentSpec(BaseModel):
    id: str
    workspace_id: str

    name: str
    role_title: str
    department_key: str

    email: Optional[str] = None
    phone: Optional[str] = None

    status: HumanAgentStatus = "draft"
    active: bool = True

    team_ids: List[str] = Field(default_factory=list)
    function_ids: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)

    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "HumanAgentSpec":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return HumanAgentSpec(**data)