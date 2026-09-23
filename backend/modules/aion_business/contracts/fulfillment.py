from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


FulfillmentMode = Literal[
    "onsite_service",
    "remote_service",
    "hybrid_service",
    "digital_delivery",
    "physical_delivery",
    "other",
]

FulfillmentStatus = Literal["draft", "active", "inactive"]


class FulfillmentProcess(BaseModel):
    id: str
    workspace_id: str

    name: str
    fulfillment_mode: FulfillmentMode = "onsite_service"
    status: FulfillmentStatus = "draft"

    description: Optional[str] = None

    service_ids: List[str] = Field(default_factory=list)
    channel_ids: List[str] = Field(default_factory=list)

    stages: List[str] = Field(default_factory=list)
    handoff_points: List[str] = Field(default_factory=list)

    average_lead_time_days: Optional[float] = None
    average_delivery_time_days: Optional[float] = None

    requires_booking: bool = False
    requires_scheduling: bool = False
    requires_manual_confirmation: bool = False

    active: bool = True
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "FulfillmentProcess":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return FulfillmentProcess(**data)