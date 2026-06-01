from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


EVENT_TYPE = "website_intake.trigger.created"
DEFAULT_BUSINESS_ID = "home_fixed"
DEFAULT_WORKFLOW_ID = "home_fixed_new_enquiry"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WebsiteIntakeCustomer:
    name: str = "Website visitor"
    phone: str = ""
    email: str = ""


@dataclass(frozen=True)
class WebsiteIntakeRequest:
    message: str
    detected_service: str
    location: str
    urgency: str


@dataclass(frozen=True)
class WebsiteIntakeTrigger:
    business_id: str
    source: str
    channel: str
    customer: WebsiteIntakeCustomer
    request: WebsiteIntakeRequest
    workflow_trigger: dict[str, Any]
    guards: dict[str, bool]
    event_type: str = EVENT_TYPE
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        seed = "|".join(
            [
                self.event_type,
                self.business_id,
                self.source,
                self.channel,
                self.request.message,
                self.request.detected_service,
                self.request.location,
                self.request.urgency,
                self.workflow_trigger.get("workflow_id", ""),
            ]
        )
        trigger_id = f"wit_{_stable_hash(seed)[:16]}"

        return {
            "event_type": self.event_type,
            "trigger_id": trigger_id,
            "business_id": self.business_id,
            "source": self.source,
            "channel": self.channel,
            "created_at": self.created_at,
            "customer": {
                "name": self.customer.name,
                "phone": self.customer.phone,
                "email": self.customer.email,
            },
            "request": {
                "message": self.request.message,
                "detected_service": self.request.detected_service,
                "location": self.request.location,
                "urgency": self.request.urgency,
            },
            "workflow_trigger": dict(self.workflow_trigger),
            "guards": dict(self.guards),
        }


def default_preview_guards() -> dict[str, bool]:
    return {
        "booking_created": False,
        "payment_created": False,
        "escrow_created": False,
        "external_message_sent": False,
        "live_chain_write": False,
        "live_execution_allowed": False,
        "human_review_required": True,
        "preview_only": True,
    }


def build_home_fixed_preview_trigger() -> dict[str, Any]:
    trigger = WebsiteIntakeTrigger(
        business_id=DEFAULT_BUSINESS_ID,
        source="home_fixed_website",
        channel="website_form",
        customer=WebsiteIntakeCustomer(
            name="Website visitor",
            phone="+34 preview",
            email="preview@example.com",
        ),
        request=WebsiteIntakeRequest(
            message="Hi, I need a leaking pergola roof repaired in Arboleas. Water is coming through near the wall after rain.",
            detected_service="Pergola / roof repair",
            location="Arboleas, Almería",
            urgency="Medium / rain-related",
        ),
        workflow_trigger={
            "workflow_id": DEFAULT_WORKFLOW_ID,
            "entry_node": "new_website_enquiry",
            "mode": "guarded_preview",
            "next_action": "create_ticket_preview",
        },
        guards=default_preview_guards(),
    )
    return trigger.to_dict()


def assert_preview_safe(trigger: dict[str, Any]) -> None:
    guards = trigger.get("guards") or {}

    forbidden = [
        "booking_created",
        "payment_created",
        "escrow_created",
        "external_message_sent",
        "live_chain_write",
        "live_execution_allowed",
    ]

    for key in forbidden:
        if guards.get(key) is True:
            raise ValueError(f"Unsafe website intake trigger: {key} must not be true")

    if guards.get("human_review_required") is not True:
        raise ValueError("Unsafe website intake trigger: human_review_required must be true")

    if guards.get("preview_only") is not True:
        raise ValueError("Unsafe website intake trigger: preview_only must be true")
