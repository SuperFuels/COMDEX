"""AION Universal Vertical Adapter preview contract.

This module keeps the AION Gateway universal across industries by mapping
vertical-specific business language into a stable machine-readable adapter shape.

The adapter is preview-only. It MUST NOT create bookings, jobs, payments,
escrow, dispatches, chain writes, or outbound messages.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping


UNIVERSAL_VERTICAL_ADAPTER_VERSION = "aion.universal_vertical_adapter.v0.1"

FUTURE_VERTICAL_KEYS = (
    "home_repair",
    "legal",
    "ecommerce",
    "hospitality",
    "clinic",
    "property",
    "b2b_supplier",
)

UNIVERSAL_FIELD_KEYS = (
    "business",
    "customer",
    "intent",
    "service",
    "quote",
    "availability",
    "booking_preview",
    "evidence",
    "proof",
    "trust",
    "human_review",
    "handoff",
)

HOME_REPAIR_FIELD_MAP = {
    "jobs": "service",
    "quotes": "quote",
    "availability": "availability",
    "evidence": "evidence",
    "proof_receipts": "proof",
    "trust_summary": "trust",
    "human_review_handoff": "human_review",
}


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_universal_vertical_adapter_contract(
    *,
    business_id: str = "home_fixed",
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    industry_key: str = "trades",
    vertical_fields: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a deterministic preview-only universal vertical adapter contract."""

    source_fields = deepcopy(dict(vertical_fields or {}))

    if vertical_key == "home_repair":
        field_map = dict(HOME_REPAIR_FIELD_MAP)
    else:
        field_map = {}

    universal_shape = {
        key: {
            "present": key in field_map.values(),
            "source_fields": sorted(
                src for src, dst in field_map.items() if dst == key
            ),
        }
        for key in UNIVERSAL_FIELD_KEYS
    }

    payload: Dict[str, Any] = {
        "adapter_version": UNIVERSAL_VERTICAL_ADAPTER_VERSION,
        "business_id": business_id,
        "business_name": business_name,
        "vertical_key": vertical_key,
        "industry_key": industry_key,
        "adapter_scope": "universal_preview",
        "supported_verticals": list(FUTURE_VERTICAL_KEYS),
        "universal_fields": list(UNIVERSAL_FIELD_KEYS),
        "vertical_field_map": field_map,
        "vertical_fields_preview": source_fields,
        "universal_shape": universal_shape,
        "compatibility": {
            "gateway_is_trade_only": False,
            "supports_home_repair": True,
            "supports_future_legal": True,
            "supports_future_ecommerce": True,
            "supports_future_hospitality": True,
            "supports_future_clinic": True,
            "supports_future_property": True,
            "supports_future_b2b_supplier": True,
        },
        "safety_profile": {
            "preview_only": True,
            "human_review_required": True,
            "would_create_booking": False,
            "would_create_live_job": False,
            "would_execute_goal_engine": False,
            "would_move_money": False,
            "would_move_pho": False,
            "would_require_wallet": False,
            "would_create_payment": False,
            "would_create_escrow": False,
            "would_release_funds": False,
            "would_send_external_messages": False,
            "would_dispatch_job": False,
            "would_write_live_chain": False,
            "public_route_mounted": False,
        },
    }

    hash_payload = deepcopy(payload)
    payload["adapter_hash"] = _canonical_hash(hash_payload)
    payload["summary_hash"] = _canonical_hash(
        {
            "adapter_version": payload["adapter_version"],
            "business_id": payload["business_id"],
            "vertical_key": payload["vertical_key"],
            "adapter_hash": payload["adapter_hash"],
            "safety_profile": payload["safety_profile"],
        }
    )
    return payload


def build_home_fixed_universal_vertical_adapter() -> Dict[str, Any]:
    """Build the Home Fixed concrete preview adapter using the universal contract."""

    return build_universal_vertical_adapter_contract(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        industry_key="trades",
        vertical_fields={
            "jobs": ["repair_request", "quote_request", "evidence_capture"],
            "quotes": ["quote_preview", "human_review_before_acceptance"],
            "availability": ["preview_available", "human_confirmed_only"],
            "evidence": ["before_photo", "after_photo", "work_note"],
            "proof_receipts": ["glyphchain_proof_receipt_preview"],
            "trust_summary": ["read_model_only"],
            "human_review_handoff": ["waiting_human_review"],
        },
    )


def build_universal_vertical_adapter_summary(
    adapter: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a compact deterministic summary for docs/tests/UI preview."""

    source = dict(adapter or build_home_fixed_universal_vertical_adapter())
    summary = {
        "adapter_version": source["adapter_version"],
        "business_id": source["business_id"],
        "vertical_key": source["vertical_key"],
        "supported_verticals": source["supported_verticals"],
        "universal_fields": source["universal_fields"],
        "adapter_hash": source["adapter_hash"],
        "preview_only": source["safety_profile"]["preview_only"],
        "human_review_required": source["safety_profile"]["human_review_required"],
        "gateway_is_trade_only": source["compatibility"]["gateway_is_trade_only"],
    }
    summary["summary_hash"] = _canonical_hash(summary)
    return summary
