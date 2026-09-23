from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from backend.modules.aion_website_intake.home_fixed_adapter import (
    normalize_home_fixed_website_payload,
)
from backend.modules.aion_website_intake.trigger_contract import assert_preview_safe


PUBLIC_INTAKE_EVENT = "website_intake.public_endpoint.received"
DEFAULT_ALLOWED_BUSINESSES = {"home_fixed"}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def create_ticket_preview_id(trigger: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(trigger).encode("utf-8")).hexdigest()[:16]
    business_id = str(trigger.get("business_id") or "business")
    return f"ticket_preview_{business_id}_{digest}"


def _response_guard() -> dict[str, bool]:
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


def _reject(reason: str, status_code: int = 400) -> dict[str, Any]:
    return {
        "ok": False,
        "status_code": status_code,
        "error": reason,
        "guards": _response_guard(),
    }


def handle_public_website_intake_post(
    payload: dict[str, Any],
    *,
    business_id: str = "home_fixed",
    origin: str | None = None,
    allowed_businesses: set[str] | None = None,
) -> dict[str, Any]:
    allowed = allowed_businesses or DEFAULT_ALLOWED_BUSINESSES

    if business_id not in allowed:
        return _reject("business_not_allowed", 403)

    if not isinstance(payload, dict):
        return _reject("payload_must_be_object", 400)

    if business_id != "home_fixed":
        return _reject("adapter_not_available", 404)

    trigger_input = dict(payload)
    trigger_input.setdefault("business_id", business_id)
    trigger_input.setdefault("source", "public_website_intake_endpoint")
    trigger_input.setdefault("channel", "website_form")

    trigger = normalize_home_fixed_website_payload(trigger_input)
    assert_preview_safe(trigger)

    ticket_preview_id = create_ticket_preview_id(trigger)

    return {
        "ok": True,
        "status_code": 202,
        "event_type": PUBLIC_INTAKE_EVENT,
        "ticket_preview_id": ticket_preview_id,
        "business_id": business_id,
        "origin": origin or "unknown",
        "trigger": trigger,
        "guards": _response_guard(),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "next": {
            "boardroom": "ticket_preview_available",
            "workflow_mode": "guarded_preview",
            "human_review_required": True,
        },
    }


def preview_home_fixed_public_intake() -> dict[str, Any]:
    return handle_public_website_intake_post(
        {
            "name": "Home Fixed Test Customer",
            "phone": "+34 600 000 000",
            "email": "test@example.com",
            "message": "Hi, I need a leaking pergola roof repaired in Arboleas. Water is coming through after rain.",
            "location": "Arboleas, Almería",
            "source": "home_fixed_website_form",
        },
        business_id="home_fixed",
        origin="https://homefixed.example",
    )
