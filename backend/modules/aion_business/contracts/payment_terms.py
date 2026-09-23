from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


PaymentMethod = Literal[
    "cash",
    "card",
    "bank_transfer",
    "direct_debit",
    "payment_link",
    "invoice",
    "marketplace_settlement",
    "other",
]

PaymentTiming = Literal[
    "upfront",
    "on_booking",
    "on_delivery",
    "net_7",
    "net_14",
    "net_30",
    "net_60",
    "milestone",
    "subscription",
    "custom",
]

PaymentTermsStatus = Literal["draft", "active", "inactive"]


class PaymentTerms(BaseModel):
    id: str
    workspace_id: str

    name: str
    status: PaymentTermsStatus = "draft"

    description: Optional[str] = None
    currency: str = "EUR"

    payment_methods: List[PaymentMethod] = Field(default_factory=list)
    timing: PaymentTiming = "custom"

    deposit_required: bool = False
    deposit_amount: Optional[float] = None
    deposit_percent: Optional[float] = None

    late_fee_percent: Optional[float] = None
    settlement_delay_days: Optional[int] = None

    channel_ids: List[str] = Field(default_factory=list)
    service_ids: List[str] = Field(default_factory=list)

    active: bool = True
    tags: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> "PaymentTerms":
        data = self.model_dump(mode="json")
        data["updated_at"] = utc_now_iso()
        return PaymentTerms(**data)