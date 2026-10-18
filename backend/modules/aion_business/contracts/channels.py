from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


ChannelType = Literal[
    "website",
    "directory",
    "marketplace",
    "social",
    "phone",
    "email",
    "whatsapp",
    "referral",
    "paid_ads",
    "offline",
    "other",
]

ChannelStatus = Literal["draft", "active", "inactive"]


class BusinessChannel(BaseModel):
    id: str
    workspace_id: str

    name: str
    slug: str
    channel_type: ChannelType = "other"

    description: Optional[str] = None
    platform_name: Optional[str] = None
    external_ref: Optional[str] = None
    public_url: Optional[str] = None

    active: bool = True
    status: ChannelStatus = "draft"

    primary_use_cases: List[str] = Field(default_factory=list)
    service_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "BusinessChannel":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return BusinessChannel(**data)