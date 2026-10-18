from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


DepartmentKey = Literal[
    "ceo",
    "coo",
    "marketing",
    "sales",
    "operations",
    "finance",
    "support",
    "hr",
    "other",
]

FunctionStatus = Literal["draft", "active", "inactive"]


class BusinessFunctionSpec(BaseModel):
    id: str
    workspace_id: str

    department_key: DepartmentKey
    key: str
    name: str
    description: Optional[str] = None

    status: FunctionStatus = "draft"
    active: bool = True

    channel_ids: List[str] = Field(default_factory=list)
    service_ids: List[str] = Field(default_factory=list)
    revenue_stream_ids: List[str] = Field(default_factory=list)
    cost_item_ids: List[str] = Field(default_factory=list)
    payment_terms_ids: List[str] = Field(default_factory=list)
    fulfillment_process_ids: List[str] = Field(default_factory=list)

    human_agent_ids: List[str] = Field(default_factory=list)
    ai_agent_ids: List[str] = Field(default_factory=list)

    escalation_targets: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "BusinessFunctionSpec":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return BusinessFunctionSpec(**data)