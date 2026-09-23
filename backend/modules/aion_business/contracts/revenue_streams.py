from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


RevenueStreamType = Literal[
    "service_sales",
    "retainer",
    "project_work",
    "callout_fee",
    "subscription",
    "commission",
    "advertising",
    "other",
]

RevenueCadence = Literal[
    "one_off",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
    "variable",
]

RevenueStreamStatus = Literal["draft", "active", "inactive"]


class RevenueStream(BaseModel):
    id: str
    workspace_id: str

    name: str
    stream_type: RevenueStreamType = "service_sales"
    cadence: RevenueCadence = "variable"
    status: RevenueStreamStatus = "draft"

    description: Optional[str] = None
    currency: str = "EUR"

    channel_ids: List[str] = Field(default_factory=list)
    service_ids: List[str] = Field(default_factory=list)

    default_value: Optional[float] = None
    recurring_amount: Optional[float] = None
    average_order_value: Optional[float] = None

    active: bool = True
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "RevenueStream":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return RevenueStream(**data)