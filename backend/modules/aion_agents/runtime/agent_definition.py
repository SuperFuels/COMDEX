from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    role_type: Literal["system", "managed", "user_defined"] = "managed"
    owner_type: Literal["aion", "ceo", "user", "system"] = "user"
    department_key: Optional[str] = None
    status: Literal["draft", "active", "inactive", "archived"] = "draft"
    execution_mode: Literal["draft_only", "draft_and_approval", "autonomous"] = (
        "draft_and_approval"
    )
    allowed_tools: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    workflow_ids: List[str] = Field(default_factory=list)
    trigger_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str