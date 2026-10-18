from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


CostType = Literal[
    "fixed_overhead",
    "labor",
    "materials",
    "subcontractor",
    "software",
    "marketing",
    "payment_fee",
    "logistics",
    "other",
]

CostFrequency = Literal[
    "one_off",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
    "per_job",
    "variable",
]

CostStatus = Literal["draft", "active", "inactive"]


class CostLineItem(BaseModel):
    id: str
    workspace_id: str

    name: str
    cost_type: CostType = "other"
    frequency: CostFrequency = "monthly"
    status: CostStatus = "draft"

    description: Optional[str] = None
    currency: str = "EUR"

    default_amount: Optional[float] = None
    unit_cost: Optional[float] = None

    channel_ids: List[str] = Field(default_factory=list)
    service_ids: List[str] = Field(default_factory=list)

    active: bool = True
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "CostLineItem":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return CostLineItem(**data)