"""
AION Agent Gateway v0 inbound preview router.

This module is backend-only and preview/audit-only.
It must not create real FulfilmentJob records or execute Goal Engine.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import hashlib
import json

from backend.modules.aion_gateway.contracts import (
    GATEWAY_PROTOCOL_VERSION,
    SUPPORTED_V0_SOURCE_CHANNELS,
    FulfilmentJobPreview,
    GatewayPreviewResult,
    NormalizedInboundIntent,
    utc_now_iso,
)
from backend.modules.aion_gateway.safety import enforce_dry_run_only



def stable_intent_hash(
    *,
    gateway_protocol_version: str,
    business_id: str,
    source_channel: str,
    intent_type: str,
    normalized_payload: Dict[str, Any],
) -> str:
    """
    Stable audit/proof hash for replay, evidence anchoring, and future GlyphChain proof.

    This hash MUST NOT grant permission or trigger execution.
    It intentionally excludes raw_payload.
    """
    canonical = {
        "gateway_protocol_version": str(gateway_protocol_version or ""),
        "business_id": str(business_id or "").lower(),
        "source_channel": str(source_channel or "").lower(),
        "intent_type": str(intent_type or "").lower(),
        "normalized_payload": normalized_payload or {},
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def preview_inbound_gateway_intent(
    *,
    business_id: str,
    source_channel: str,
    vertical_key: str,
    intent_type: str,
    raw_payload: Dict[str, Any],
    gateway_protocol_version: str = GATEWAY_PROTOCOL_VERSION,
    gateway_session_id: str = "",
    trace_context: Optional[Dict[str, Any]] = None,
    priority: str = "normal",
    dry_run_only: bool = True,
) -> Dict[str, Any]:
    """
    Preview an inbound gateway intent.

    v0 contract:
    - no public API
    - no provider calls
    - no workflow execution
    - no business mutation
    - no real FulfilmentJob creation
    """
    return _preview_inbound_gateway_intent_guarded(
        business_id=business_id,
        source_channel=source_channel,
        vertical_key=vertical_key,
        intent_type=intent_type,
        raw_payload=raw_payload,
        gateway_protocol_version=gateway_protocol_version,
        gateway_session_id=gateway_session_id,
        trace_context=trace_context or {},
        priority=priority,
        dry_run_only=dry_run_only,
    )


@enforce_dry_run_only
def _preview_inbound_gateway_intent_guarded(
    *,
    business_id: str,
    source_channel: str,
    vertical_key: str,
    intent_type: str,
    raw_payload: Dict[str, Any],
    gateway_protocol_version: str,
    gateway_session_id: str,
    trace_context: Dict[str, Any],
    priority: str,
    dry_run_only: bool = True,
) -> Dict[str, Any]:
    blocked_reasons = []

    business_id_norm = str(business_id or "").strip()
    source_channel_norm = str(source_channel or "").strip().lower()
    intent_type_norm = str(intent_type or "").strip().lower()
    vertical_key_norm = str(vertical_key or "").strip().lower()

    if not business_id_norm:
        blocked_reasons.append("missing_business_id")

    if not isinstance(raw_payload, dict) or not raw_payload:
        blocked_reasons.append("missing_raw_payload")

    if source_channel_norm not in SUPPORTED_V0_SOURCE_CHANNELS:
        blocked_reasons.append("unsupported_source_channel")

    if not intent_type_norm:
        blocked_reasons.append("invalid_intent_type")

    normalized_payload = {
        "vertical_key": vertical_key_norm,
        "intent_type": intent_type_norm,
        "summary": str(raw_payload.get("message") or raw_payload.get("summary") or "").strip()
        if isinstance(raw_payload, dict)
        else "",
    }

    intent_hash = stable_intent_hash(
        gateway_protocol_version=gateway_protocol_version,
        business_id=business_id_norm,
        source_channel=source_channel_norm,
        intent_type=intent_type_norm,
        normalized_payload=normalized_payload,
    )

    customer_context = {
        "name": raw_payload.get("name", "") if isinstance(raw_payload, dict) else "",
        "email": raw_payload.get("email", "") if isinstance(raw_payload, dict) else "",
        "phone": raw_payload.get("phone", "") if isinstance(raw_payload, dict) else "",
    }

    requested_outcome = (
        str(raw_payload.get("requested_outcome") or raw_payload.get("message") or "").strip()
        if isinstance(raw_payload, dict)
        else ""
    )

    intent = NormalizedInboundIntent(
        intent_id=f"intent_preview_{business_id_norm or 'missing'}_{source_channel_norm or 'missing'}",
        gateway_protocol_version=gateway_protocol_version,
        gateway_session_id=gateway_session_id,
        trace_context=dict(trace_context or {}),
        business_id=business_id_norm,
        source_channel=source_channel_norm,
        vertical_key=vertical_key_norm,
        intent_type=intent_type_norm,
        raw_payload=dict(raw_payload or {}),
        normalized_payload=normalized_payload,
        intent_hash=intent_hash,
        customer_context=customer_context,
        requested_outcome=requested_outcome,
        priority=priority if priority in {"normal", "urgent", "emergency"} else "normal",
        dry_run_only=True,
        requires_human_review=True,
        blocked_reasons=list(blocked_reasons),
        metadata={"gateway_v0_preview_only": True},
    )

    preview = FulfilmentJobPreview(
        job_preview_id=f"job_preview_{intent.intent_id}",
        intent_id=intent.intent_id,
        business_id=business_id_norm,
        workflow_hint=f"{vertical_key_norm}.{intent_type_norm}".strip("."),
        suggested_goal_hint=f"Review inbound {intent_type_norm or 'intent'} for {vertical_key_norm or 'unknown_vertical'}",
        customer_context=customer_context,
        requested_outcome=requested_outcome,
        routing_status="blocked" if blocked_reasons else "preview_ready",
        evidence_requirements=[],
        risk_flags=[],
        safety_flags=["dry_run_only", "requires_human_review", "no_live_execution"],
        would_create_fulfilment_job=False,
        would_execute_goal_engine=False,
        requires_human_review=True,
        metadata={"created_at": utc_now_iso()},
    )

    machine_trace = {
        "gateway_protocol_version": gateway_protocol_version,
        "gateway_session_id": gateway_session_id,
        "trace_context": dict(trace_context or {}),
        "intent_hash": intent_hash,
        "source_channel": source_channel_norm,
        "intent_type": intent_type_norm,
        "blocked_reasons": list(blocked_reasons),
        "dry_run_only": True,
        "would_create_fulfilment_job": False,
        "would_execute_goal_engine": False,
        "would_write_externally": False,
        "would_mutate_business_state": False,
        "would_grant_permission": False,
    }

    return GatewayPreviewResult(
        ok=not bool(blocked_reasons),
        normalized_inbound_intent=intent.to_dict(),
        fulfilment_job_preview=preview.to_dict(),
        machine_trace=machine_trace,
        blocked_reasons=list(blocked_reasons),
    ).to_dict()
