from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


TeamStatus = Literal["draft", "active", "inactive"]


class TeamSpec(BaseModel):
    id: str
    workspace_id: str

    name: str
    department_key: str
    description: Optional[str] = None

    status: TeamStatus = "draft"
    active: bool = True

    human_agent_ids: List[str] = Field(default_factory=list)
    ai_agent_ids: List[str] = Field(default_factory=list)
    function_ids: List[str] = Field(default_factory=list)

    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "TeamSpec":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return TeamSpec(**data)