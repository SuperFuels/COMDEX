from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


ServiceStatus = Literal["draft", "active", "inactive"]
ServiceDeliveryMode = Literal["onsite", "remote", "hybrid"]
ServicePricingType = Literal["fixed", "hourly", "quote", "retainer", "custom"]


class ServiceOffer(BaseModel):
    id: str
    workspace_id: str

    name: str
    slug: str
    category: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None

    delivery_mode: ServiceDeliveryMode = "onsite"
    pricing_type: ServicePricingType = "quote"

    base_price: Optional[float] = None
    currency: str = "EUR"

    estimated_duration_minutes: Optional[int] = None
    service_area: List[str] = Field(default_factory=list)

    requires_booking: bool = False
    requires_quote: bool = True
    active: bool = True
    status: ServiceStatus = "draft"

    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "ServiceOffer":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return ServiceOffer(**data)