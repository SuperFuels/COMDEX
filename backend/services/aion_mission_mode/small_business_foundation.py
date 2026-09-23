"""AION Phase 24B — Small Business Foundation Quick Start.

This module creates the first useful foundation object for an existing small
business. It is intentionally quick-start first: only a few fields are required;
website scan, document upload, social profiles and fuller details can enrich it
later.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any


SCHEMA_VERSION = "aion.small_business_foundation.v0"
MODE = "small_business_growth"

REQUIRED_FIELDS = (
    "business_name",
    "business_type",
    "industry",
    "service_area",
    "primary_goal",
)

ALLOWED_BUSINESS_TYPES = {
    "services",
    "products",
    "both",
    "unknown",
}

ALLOWED_PRIMARY_GOALS = {
    "get_more_leads",
    "automate_work",
    "improve_operations",
    "grow_revenue",
    "organise_business",
    "unknown",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_multiline(value: Any) -> str:
    text = _clean_text(value)
    return re.sub(r"\n{3,}", "\n\n", text)


def _slug(value: Any, fallback: str = "business") -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def _normalise_choice(value: Any, allowed: set[str], fallback: str = "unknown") -> str:
    cleaned = _slug(value, fallback=fallback).replace("-", "_")
    return cleaned if cleaned in allowed else fallback


def _normalise_socials(value: Any) -> list[str]:
    if isinstance(value, list):
      raw_items = value
    else:
      raw_items = re.split(r"[\n,]+", _clean_text(value))

    socials: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        socials.append(cleaned)
    return socials


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash_payload(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def validate_small_business_foundation_input(data: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if not _clean_text(data.get(field))]
    return {
        "valid": not missing,
        "missing_required_fields": missing,
        "required_fields": list(REQUIRED_FIELDS),
    }


def create_staged_enrichment_tasks(data: dict[str, Any]) -> list[dict[str, Any]]:
    website = _clean_text(data.get("website"))
    documents = data.get("uploaded_documents") or []
    socials = _normalise_socials(data.get("social_accounts") or data.get("social_handles"))

    tasks: list[dict[str, Any]] = []

    if website:
        tasks.append({
            "task_id": "website_scan",
            "title": "Scan website for business details",
            "source": "website",
            "status": "staged",
            "tool_mode": "read_only_external",
            "live_external_side_effect": False,
            "approval_required": False,
        })

    if documents:
        tasks.append({
            "task_id": "document_extract",
            "title": "Extract details from uploaded documents",
            "source": "uploaded_documents",
            "status": "staged",
            "tool_mode": "safe_internal",
            "live_external_side_effect": False,
            "approval_required": False,
        })

    if socials:
        tasks.append({
            "task_id": "social_profile_read",
            "title": "Read social profile context",
            "source": "social_accounts",
            "status": "staged",
            "tool_mode": "read_only_external",
            "live_external_side_effect": False,
            "approval_required": False,
        })

    tasks.append({
        "task_id": "manual_foundation_review",
        "title": "User reviews and edits foundation",
        "source": "manual_details",
        "status": "ready",
        "tool_mode": "safe_internal",
        "live_external_side_effect": False,
        "approval_required": False,
    })

    return tasks


def create_small_business_foundation_profile(data: dict[str, Any]) -> dict[str, Any]:
    source = deepcopy(data or {})
    validation = validate_small_business_foundation_input(source)

    if not validation["valid"]:
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": MODE,
            "status": "needs_required_fields",
            "validation": validation,
            "foundation_hash": None,
            "live_external_side_effect": False,
        }

    business_name = _clean_text(source.get("business_name"))
    business_id = _slug(source.get("business_id") or business_name)
    business_type = _normalise_choice(source.get("business_type"), ALLOWED_BUSINESS_TYPES)
    primary_goal = _normalise_choice(source.get("primary_goal"), ALLOWED_PRIMARY_GOALS)

    profile_core = {
        "schema_version": SCHEMA_VERSION,
        "mode": MODE,
        "business_id": business_id,
        "business_name": business_name,
        "business_type": business_type,
        "industry": _clean_text(source.get("industry")),
        "service_area": _clean_text(source.get("service_area")),
        "primary_goal": primary_goal,
        "website": _clean_text(source.get("website")),
        "social_accounts": _normalise_socials(source.get("social_accounts") or source.get("social_handles")),
        "products_services": _clean_multiline(source.get("products_services") or source.get("services_products")),
        "target_customers": _clean_multiline(source.get("target_customers")),
        "revenue_streams": _clean_multiline(source.get("revenue_streams")),
        "team_size": _clean_text(source.get("team_size")),
        "brand_assets": _clean_multiline(source.get("brand_assets")),
        "tone_of_voice": _clean_multiline(source.get("tone_of_voice")),
        "current_tools": _clean_multiline(source.get("current_tools")),
        "current_pain_points": _clean_multiline(source.get("current_pain_points") or source.get("pain_points")),
        "growth_goals": _clean_multiline(source.get("growth_goals")),
        "contact_email": _clean_text(source.get("contact_email")),
        "phone_number": _clean_text(source.get("phone_number")),
        "business_address": _clean_multiline(source.get("business_address")),
        "opening_hours": _clean_multiline(source.get("opening_hours")),
        "pricing_notes": _clean_multiline(source.get("pricing_notes")),
        "brand_notes": _clean_multiline(source.get("brand_notes")),
        "reviews_or_proof": _clean_multiline(source.get("reviews_or_proof")),
        "extra_notes": _clean_multiline(source.get("extra_notes")),
        "optional_fields_can_be_completed_later": True,
        "live_external_side_effect": False,
    }

    enrichment_tasks = create_staged_enrichment_tasks(source)
    hash_input = {
        **profile_core,
        "staged_enrichment_tasks": enrichment_tasks,
    }

    foundation_hash = _hash_payload(hash_input)

    return {
        **profile_core,
        "status": "draft_ready_for_review",
        "validation": validation,
        "staged_enrichment_tasks": enrichment_tasks,
        "department_readiness": {
            "pilot": "ready",
            "marketing": "ready_after_foundation_approval",
            "sales": "ready_after_foundation_approval",
            "finance": "ready_after_foundation_approval",
            "operations": "ready_after_foundation_approval",
            "support": "ready_after_foundation_approval",
            "builder": "ready_after_foundation_approval",
        },
        "foundation_hash": foundation_hash,
        "created_at": _now_iso(),
    }


def summarize_small_business_foundation(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile or profile.get("status") == "needs_required_fields":
        return {
            "status": profile.get("status") if isinstance(profile, dict) else "missing",
            "ready_for_approval": False,
            "missing_required_fields": profile.get("validation", {}).get("missing_required_fields", []) if isinstance(profile, dict) else list(REQUIRED_FIELDS),
        }

    optional_fields = [
        "website",
        "social_accounts",
        "products_services",
        "target_customers",
        "revenue_streams",
        "team_size",
        "brand_assets",
        "tone_of_voice",
        "current_tools",
        "current_pain_points",
        "growth_goals",
        "contact_email",
        "phone_number",
        "business_address",
        "opening_hours",
        "pricing_notes",
        "brand_notes",
        "reviews_or_proof",
        "extra_notes",
    ]

    completed_optional = [
        field for field in optional_fields
        if profile.get(field) not in ("", [], None)
    ]

    return {
        "status": profile.get("status"),
        "ready_for_approval": True,
        "business_id": profile.get("business_id"),
        "business_name": profile.get("business_name"),
        "mode": profile.get("mode"),
        "business_type": profile.get("business_type"),
        "industry": profile.get("industry"),
        "service_area": profile.get("service_area"),
        "primary_goal": profile.get("primary_goal"),
        "completed_optional_fields": completed_optional,
        "missing_optional_fields": [field for field in optional_fields if field not in completed_optional],
        "staged_enrichment_count": len(profile.get("staged_enrichment_tasks") or []),
        "foundation_hash": profile.get("foundation_hash"),
    }
