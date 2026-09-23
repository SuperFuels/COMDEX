"""
AION Agent Gateway v0 contracts.

The gateway normalizes messy inbound channels into:
- NormalizedInboundIntent
- FulfilmentJobPreview

v0 is preview/audit only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime, timezone


GatewaySourceChannel = Literal[
    "legacy_web_form",
    "agent_protocol",
    "website_button",
    "embedded_chat",
    "agent_email",
    "whatsapp",
    "slack",
    "voice",
]

GatewayPriority = Literal["normal", "urgent", "emergency"]

GATEWAY_PROTOCOL_VERSION = "aion.gateway.v0.1"

SUPPORTED_V0_SOURCE_CHANNELS = {
    "legacy_web_form",
    "agent_protocol",
}

RESERVED_SOURCE_CHANNELS = {
    "website_button",
    "embedded_chat",
    "agent_email",
    "whatsapp",
    "slack",
    "voice",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class NormalizedInboundIntent:
    intent_id: str
    gateway_protocol_version: str
    gateway_session_id: str
    trace_context: Dict[str, Any]
    business_id: str
    source_channel: str
    vertical_key: str
    intent_type: str
    raw_payload: Dict[str, Any]
    normalized_payload: Dict[str, Any]
    intent_hash: str
    customer_context: Dict[str, Any]
    requested_outcome: str
    priority: GatewayPriority = "normal"
    created_at: str = field(default_factory=utc_now_iso)
    dry_run_only: bool = True
    requires_human_review: bool = True
    blocked_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FulfilmentJobPreview:
    job_preview_id: str
    intent_id: str
    business_id: str
    workflow_hint: str
    suggested_goal_hint: str
    customer_context: Dict[str, Any]
    requested_outcome: str
    routing_status: str
    evidence_requirements: List[Dict[str, Any]] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    safety_flags: List[str] = field(default_factory=list)
    would_create_fulfilment_job: bool = False
    would_execute_goal_engine: bool = False
    requires_human_review: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GatewayPreviewResult:
    ok: bool
    normalized_inbound_intent: Dict[str, Any]
    fulfilment_job_preview: Dict[str, Any]
    machine_trace: Dict[str, Any]
    blocked_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
