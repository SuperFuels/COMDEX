from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from backend.modules.aion_website_intake.public_intake_endpoint import (
    create_ticket_preview_id,
    preview_home_fixed_public_intake,
)
from backend.modules.aion_website_intake.trigger_contract import assert_preview_safe


DEFAULT_WORKFLOW_BY_SERVICE = {
    "Pergola / roof repair": "home_fixed_new_enquiry",
    "Roof repair": "home_fixed_new_enquiry",
    "General home repair": "home_fixed_new_enquiry",
}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def create_trigger_evidence_id(trigger: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(trigger).encode("utf-8")).hexdigest()[:16]
    return f"evidence_website_intake_{digest}"


def select_workflow_for_trigger(trigger: dict[str, Any]) -> dict[str, Any]:
    business_id = trigger.get("business_id") or "unknown_business"
    request = trigger.get("request") or {}
    detected_service = request.get("detected_service") or "General home repair"

    workflow_id = DEFAULT_WORKFLOW_BY_SERVICE.get(
        detected_service,
        f"{business_id}_new_enquiry",
    )

    return {
        "business_id": business_id,
        "workflow_id": workflow_id,
        "detected_service": detected_service,
        "selection_mode": "business_id_plus_service",
        "workflow_mode": "guarded_preview",
    }


def build_business_ticket_from_trigger(trigger: dict[str, Any]) -> dict[str, Any]:
    assert_preview_safe(trigger)

    customer = trigger.get("customer") or {}
    request = trigger.get("request") or {}
    workflow = select_workflow_for_trigger(trigger)
    ticket_preview_id = create_ticket_preview_id(trigger)
    evidence_id = create_trigger_evidence_id(trigger)

    return {
        "ticket_id": ticket_preview_id,
        "ticket_type": "website_intake_ticket",
        "status": "preview_ready",
        "business_id": trigger.get("business_id"),
        "customer": customer,
        "request": request,
        "source": trigger.get("source"),
        "channel": trigger.get("channel"),
        "workflow": workflow,
        "evidence": [
            {
                "evidence_id": evidence_id,
                "type": "website_intake_trigger_payload",
                "label": "Website intake trigger",
                "payload": trigger,
            }
        ],
        "guards": {
            "booking_created": False,
            "payment_created": False,
            "escrow_created": False,
            "external_message_sent": False,
            "live_chain_write": False,
            "live_execution_allowed": False,
            "human_review_required": True,
            "preview_only": True,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def prepare_workflow_preview_from_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    workflow = ticket.get("workflow") or {}
    request = ticket.get("request") or {}

    return {
        "preview_id": f"workflow_preview_{ticket['ticket_id']}",
        "ticket_id": ticket["ticket_id"],
        "business_id": ticket.get("business_id"),
        "workflow_id": workflow.get("workflow_id"),
        "workflow_mode": "guarded_preview",
        "current_step": "workflow_entry_node",
        "suggested_next_action": "prepare_quote_preview",
        "summary": {
            "service": request.get("detected_service"),
            "location": request.get("location"),
            "urgency": request.get("urgency"),
            "message": request.get("message"),
        },
        "guards": ticket["guards"],
        "outputs": {
            "quote_preview": {
                "status": "inspection_required",
                "label": "Prepare quote preview",
                "human_review_required": True,
            }
        },
    }


def bridge_public_intake_to_workflow(public_intake_result: dict[str, Any]) -> dict[str, Any]:
    if not public_intake_result.get("ok"):
        return {
            "ok": False,
            "status": "rejected",
            "reason": public_intake_result.get("error", "public_intake_failed"),
            "guards": public_intake_result.get("guards", {}),
        }

    trigger = public_intake_result["trigger"]
    ticket = build_business_ticket_from_trigger(trigger)
    workflow_preview = prepare_workflow_preview_from_ticket(ticket)

    return {
        "ok": True,
        "status": "workflow_preview_ready",
        "ticket": ticket,
        "workflow_preview": workflow_preview,
        "guards": ticket["guards"],
    }


def preview_home_fixed_workflow_trigger_bridge() -> dict[str, Any]:
    return bridge_public_intake_to_workflow(preview_home_fixed_public_intake())
