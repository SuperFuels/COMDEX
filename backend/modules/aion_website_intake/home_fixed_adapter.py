from __future__ import annotations

from typing import Any

from backend.modules.aion_website_intake.trigger_contract import (
    DEFAULT_BUSINESS_ID,
    DEFAULT_WORKFLOW_ID,
    WebsiteIntakeCustomer,
    WebsiteIntakeRequest,
    WebsiteIntakeTrigger,
    assert_preview_safe,
    default_preview_guards,
)


SERVICE_KEYWORDS = [
    ("pergola", "Pergola / roof repair"),
    ("roof", "Roof repair"),
    ("leak", "Leak repair"),
    ("water", "Leak repair"),
    ("tile", "Tile repair"),
    ("paint", "Painting"),
    ("wall", "Wall repair"),
    ("garden", "Garden / exterior work"),
]


def _as_string(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _first_present(payload: dict[str, Any], keys: list[str], fallback: str = "") -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return _as_string(value, fallback)
    return fallback


def _flatten_multistep_payload(payload: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}

    steps = payload.get("steps") or payload.get("pages") or []
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue

            fields = step.get("fields") or step.get("answers") or []
            if isinstance(fields, list):
                for field in fields:
                    if not isinstance(field, dict):
                        continue
                    key = (
                        field.get("name")
                        or field.get("key")
                        or field.get("id")
                        or field.get("label")
                    )
                    value = field.get("value", field.get("answer"))
                    if key:
                        flat[str(key).strip().lower().replace(" ", "_")] = value

    answers = payload.get("answers") or payload.get("fields") or {}
    if isinstance(answers, dict):
        for key, value in answers.items():
            flat[str(key).strip().lower().replace(" ", "_")] = value

    if isinstance(answers, list):
        for field in answers:
            if not isinstance(field, dict):
                continue
            key = field.get("name") or field.get("key") or field.get("id") or field.get("label")
            value = field.get("value", field.get("answer"))
            if key:
                flat[str(key).strip().lower().replace(" ", "_")] = value

    merged = dict(payload)
    merged.update(flat)
    return merged


def classify_home_fixed_service(message: str, explicit_service: str = "") -> str:
    if explicit_service:
        return explicit_service

    lower = message.lower()
    for keyword, service in SERVICE_KEYWORDS:
        if keyword in lower:
            return service

    return "General home repair"


def infer_home_fixed_urgency(message: str, explicit_urgency: str = "") -> str:
    if explicit_urgency:
        return explicit_urgency

    lower = message.lower()
    if any(word in lower for word in ["urgent", "emergency", "flood", "dangerous"]):
        return "High"
    if any(word in lower for word in ["rain", "leak", "water", "coming through"]):
        return "Medium / rain-related"
    return "Normal"


def normalize_home_fixed_website_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = _flatten_multistep_payload(payload)

    message = _first_present(
        data,
        ["message", "request", "enquiry", "description", "details", "job_details", "what_do_you_need"],
        "Website enquiry received",
    )

    service = classify_home_fixed_service(
        message,
        _first_present(data, ["service", "service_type", "category", "job_type"]),
    )

    location = _first_present(
        data,
        ["location", "town", "area", "address", "postcode"],
        "Location not provided",
    )

    urgency = infer_home_fixed_urgency(
        message,
        _first_present(data, ["urgency", "priority", "timeframe"]),
    )

    customer = WebsiteIntakeCustomer(
        name=_first_present(data, ["name", "full_name", "customer_name"], "Website visitor"),
        phone=_first_present(data, ["phone", "telephone", "mobile", "whatsapp"]),
        email=_first_present(data, ["email", "email_address"]),
    )

    trigger = WebsiteIntakeTrigger(
        business_id=_first_present(data, ["business_id"], DEFAULT_BUSINESS_ID),
        source=_first_present(data, ["source"], "home_fixed_website"),
        channel=_first_present(data, ["channel"], "website_form"),
        customer=customer,
        request=WebsiteIntakeRequest(
            message=message,
            detected_service=service,
            location=location,
            urgency=urgency,
        ),
        workflow_trigger={
            "workflow_id": DEFAULT_WORKFLOW_ID,
            "entry_node": "new_website_enquiry",
            "mode": "guarded_preview",
            "next_action": "create_ticket_preview",
        },
        guards=default_preview_guards(),
    ).to_dict()

    assert_preview_safe(trigger)
    return trigger


def normalize_home_fixed_simple_form(payload: dict[str, Any]) -> dict[str, Any]:
    return normalize_home_fixed_website_payload(payload)


def normalize_home_fixed_multistep_form(payload: dict[str, Any]) -> dict[str, Any]:
    return normalize_home_fixed_website_payload(payload)
