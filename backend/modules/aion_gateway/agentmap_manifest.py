from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Optional


AGENTMAP_VERSION = "aion.agentmap.v0.1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def build_agentmap_manifest(
    *,
    business_id: str,
    business_name: str,
    vertical_key: str,
    meta_description: Optional[str] = None,
    machine_description: Optional[str] = None,
    capabilities: Optional[List[Mapping[str, Any]]] = None,
    availability: Optional[Mapping[str, Any]] = None,
    accepted_protocols: Optional[List[str]] = None,
    authentication: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic machine-readable AgentMap manifest.

    This is discovery metadata only. It does not create bookings, payments,
    outbound messages, escrow mutations, or live chain writes.
    """

    human_seo_metadata = {
        "meta_description": meta_description
        or f"{business_name} service information for human website visitors.",
    }

    machine_a2a_metadata = {
        "machine_description": machine_description
        or f"Machine-readable capability manifest for {business_name}.",
        "capabilities": list(capabilities or [
            {
                "capability_key": "public_intent_preview",
                "description": "Preview a public customer intent without live side effects.",
                "preview_only": True,
                "human_review_required": True,
            },
            {
                "capability_key": "proof_receipt_lookup",
                "description": "Read proof receipt metadata and hashes without live chain writes.",
                "preview_only": True,
                "human_review_required": True,
            },
        ]),
        "availability": dict(availability or {
            "status": "preview_available",
            "live_booking_available": False,
        }),
        "accepted_protocols": list(accepted_protocols or [
            "aion.gateway.v0.1",
            "aion.a2a.v0.1",
            "aion.agentmap.v0.1",
        ]),
        "authentication": dict(authentication or {
            "required_for_discovery": False,
            "required_for_live_actions": True,
        }),
    }

    safety_profile = {
        "preview_only": True,
        "human_review_required": True,
        "would_create_booking": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "live_chain_write": False,
    }

    metadata_source = {
        "human_seo_metadata": human_seo_metadata,
        "machine_a2a_metadata": machine_a2a_metadata,
        "safety_profile": safety_profile,
    }

    manifest = {
        "agentmap_version": AGENTMAP_VERSION,
        "business_id": str(business_id),
        "business_name": str(business_name),
        "vertical_key": str(vertical_key),
        "human_seo_metadata": human_seo_metadata,
        "machine_a2a_metadata": machine_a2a_metadata,
        "safety_profile": safety_profile,
        "metadata_hash": _stable_hash(metadata_source),
    }

    manifest["agentmap_hash"] = _stable_hash(manifest)
    return manifest


def build_home_fixed_agentmap_manifest() -> Dict[str, Any]:
    return build_agentmap_manifest(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        meta_description="Home Fixed provides home repair and maintenance services.",
        machine_description="Home repair machine metadata for quote previews, evidence, availability, and proof lookup.",
    )
