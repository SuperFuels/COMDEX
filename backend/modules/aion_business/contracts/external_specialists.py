from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


ExternalActionMode = Literal["api", "human", "hybrid"]
ExternalSpecialistType = Literal[
    "provider_model",
    "native_platform_ai",
    "external_service",
    "human_specialist",
]
ExternalCostClass = Literal["low", "medium", "high", "enterprise"]


class ExternalSpecialistCapability(BaseModel):
    id: str
    label: str
    description: Optional[str] = None


class ExternalSpecialistSpec(BaseModel):
    id: str
    workspace_id: str

    name: str
    specialist_type: ExternalSpecialistType
    provider: str
    action_mode: ExternalActionMode = "api"

    capabilities: List[str] = Field(default_factory=list)
    supported_task_types: List[str] = Field(default_factory=list)

    enabled: bool = True
    priority: int = 100
    cost_class: ExternalCostClass = "medium"

    requires_byok: bool = False
    requires_human_approval: bool = False

    metadata: Dict[str, str] = Field(default_factory=dict)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class ExternalSpecialistSelection(BaseModel):
    workspace_id: str
    capability: str
    selected_specialist_id: Optional[str] = None
    fallback_specialist_ids: List[str] = Field(default_factory=list)
    reason: str = ""
    created_at: str = Field(default_factory=utc_now_iso)