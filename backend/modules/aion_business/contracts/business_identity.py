from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


BusinessType = Literal[
    "service_business",
    "ecommerce",
    "marketplace_seller",
    "agency",
    "hybrid",
]


class BusinessIdentity(BaseModel):
    """
    Minimal business identity contract for the first real onboarded business.

    v1 scope:
    - enough identity/context to drive onboarding
    - enough metadata to generate an initial topology
    - enough branding/location data to support founder view and future connectors
    """

    workspace_id: str

    business_name: str
    legal_name: Optional[str] = None
    public_brand_name: Optional[str] = None

    business_type: BusinessType = "service_business"

    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    timezone: str = "UTC"
    currency: str = "EUR"

    primary_domain: Optional[str] = None
    website_url: Optional[str] = None

    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None

    description: Optional[str] = None
    tagline: Optional[str] = None

    founder_name: Optional[str] = None
    owner_role_id: Optional[str] = "ceo-core"

    onboarding_status: str = "draft"
    active: bool = True

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def display_name(self) -> str:
        return self.public_brand_name or self.business_name

    def touch(self) -> "BusinessIdentity":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return BusinessIdentity(**data)