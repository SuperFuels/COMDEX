from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping


SCHEMA_VERSION = "aion.sovereign_brain.v1"
CANONICAL_STORE_KINDS = (
    "identity",
    "memory",
    "business_map",
    "policy",
    "capability",
    "receipt",
)
FORBIDDEN_PROVIDER_AUTHORITIES = (
    "grant_authority",
    "write_canonical_identity",
    "write_canonical_memory",
    "write_canonical_business_map",
    "write_canonical_policy",
    "erase_audit_receipts",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field}_required")
    return text


def build_brain_identity(
    *, brain_id: str, owner_id: str, public_key_fingerprint: str, created_at: str | None = None
) -> Dict[str, Any]:
    """Create a provider-independent identity for one customer-owned AION brain."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "brain_identity",
        "brain_id": _require_text(brain_id, "brain_id"),
        "owner_id": _require_text(owner_id, "owner_id"),
        "public_key_fingerprint": _require_text(public_key_fingerprint, "public_key_fingerprint"),
        "created_at": created_at or _now(),
        "canonical_stores": list(CANONICAL_STORE_KINDS),
        "provider_bindings": [],
    }


def build_business_map(
    *, brain_id: str, nodes: Iterable[Mapping[str, Any]], edges: Iterable[Mapping[str, Any]]
) -> Dict[str, Any]:
    normalized_nodes = [dict(item) for item in nodes]
    normalized_edges = [dict(item) for item in edges]
    for item in normalized_nodes + normalized_edges:
        if not str(item.get("source") or "").strip():
            raise ValueError("business_map_source_required")
        if "confidence" not in item:
            raise ValueError("business_map_confidence_required")
        confidence = float(item["confidence"])
        if confidence < 0 or confidence > 1:
            raise ValueError("business_map_confidence_out_of_range")
        item["confidence"] = confidence
        item.setdefault("review_state", "proposed")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "business_map",
        "brain_id": _require_text(brain_id, "brain_id"),
        "nodes": normalized_nodes,
        "edges": normalized_edges,
    }
    payload["content_hash"] = _hash(payload)
    return payload


def build_intelligence_route_receipt(
    *,
    brain_id: str,
    request: Mapping[str, Any],
    route: Mapping[str, Any],
    result: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> Dict[str, Any]:
    """Record routing evidence without persisting raw prompt or result content."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "intelligence_route_receipt",
        "brain_id": _require_text(brain_id, "brain_id"),
        "created_at": _now(),
        "request_hash": _hash(dict(request)),
        "result_hash": _hash(dict(result)),
        "route": dict(route),
        "disclosure": dict(disclosure),
        "budget": dict(budget),
        "raw_prompt_retained": False,
        "raw_result_retained": False,
    }


def build_brain_export_manifest(
    *, brain_identity: Mapping[str, Any], stores: Mapping[str, Mapping[str, Any]]
) -> Dict[str, Any]:
    missing = sorted(set(CANONICAL_STORE_KINDS) - set(stores))
    if missing:
        raise ValueError(f"brain_export_missing_stores:{','.join(missing)}")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "kind": "brain_export",
        "brain_id": _require_text(brain_identity.get("brain_id"), "brain_id"),
        "created_at": _now(),
        "stores": {
            name: {
                "schema_version": str(value.get("schema_version") or SCHEMA_VERSION),
                "content_hash": _hash(dict(value)),
            }
            for name, value in sorted(stores.items())
        },
        "provider_credentials_included": False,
        "model_weights_included": False,
    }
    manifest["manifest_hash"] = _hash(manifest)
    return manifest


def assert_provider_adapter_boundary(adapter_manifest: Mapping[str, Any]) -> None:
    requested = {str(item) for item in adapter_manifest.get("authorities", [])}
    forbidden = sorted(requested.intersection(FORBIDDEN_PROVIDER_AUTHORITIES))
    if forbidden:
        raise ValueError(f"provider_authority_forbidden:{','.join(forbidden)}")


def published_schemas() -> Dict[str, Dict[str, Any]]:
    """Small portable schemas for installers, exporters and non-Python clients."""
    base = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}
    return {
        "brain_identity": {
            **base,
            "$id": "aion://schemas/brain-identity/v1",
            "required": ["schema_version", "kind", "brain_id", "owner_id", "public_key_fingerprint"],
        },
        "brain_export": {
            **base,
            "$id": "aion://schemas/brain-export/v1",
            "required": ["schema_version", "kind", "brain_id", "stores", "manifest_hash"],
        },
        "business_map": {
            **base,
            "$id": "aion://schemas/business-map/v1",
            "required": ["schema_version", "kind", "brain_id", "nodes", "edges", "content_hash"],
        },
        "intelligence_route_receipt": {
            **base,
            "$id": "aion://schemas/intelligence-route-receipt/v1",
            "required": ["schema_version", "kind", "brain_id", "request_hash", "result_hash", "route"],
        },
    }
