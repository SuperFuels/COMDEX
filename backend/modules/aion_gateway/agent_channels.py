from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


AGENT_CHANNEL_PROTOCOL_VERSION = "aion.agent_channels.v0.1"

SUPPORTED_AGENT_CHANNELS = {
    "agent_email",
    "agent_phone",
    "whatsapp",
    "embedded_chat",
    "supplier_email",
    "booking_inbox",
}

RESERVED_ONLY_CHANNELS = {
    "agent_phone",
    "whatsapp",
    "embedded_chat",
    "booking_inbox",
}

PREVIEW_ENABLED_CHANNELS = {
    "agent_email",
    "supplier_email",
}


def _stable_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()



def _message_hash_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stable payload used for inbound message identity.

    Runtime envelope fields must not change message_hash.
    """
    excluded = {
        "message_hash",
        "received_at_ms",
        "created_at_ms",
        "received_at",
        "created_at",
        "timestamp",
        "timestamp_ms",
        "trace_id",
        "runtime_trace_id",
    }
    return {key: value for key, value in payload.items() if key not in excluded}


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class AgentChannel:
    channel_key: str
    display_name: str
    reserved_only: bool = True
    preview_enabled: bool = False
    can_send_externally: bool = False
    can_call_provider: bool = False
    can_mutate_job_timeline: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentInboxMessage:
    message_id: str
    business_id: str
    channel_key: str
    raw_subject: str = ""
    raw_body: str = ""
    sender_ref: str = ""
    job_id: Optional[str] = None
    received_at_ms: int = field(default_factory=_now_ms)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "protocol_version": AGENT_CHANNEL_PROTOCOL_VERSION,
            "message_id": self.message_id,
            "business_id": self.business_id,
            "channel_key": self.channel_key,
            "raw_subject": self.raw_subject,
            "raw_body": self.raw_body,
            "sender_ref": self.sender_ref,
            "job_id": self.job_id,
            "received_at_ms": int(self.received_at_ms),
            "metadata": dict(self.metadata or {}),
        }

    def to_dict(self) -> Dict[str, Any]:
        payload = self.to_payload()
        payload["message_hash"] = _stable_hash(_message_hash_payload(payload))
        return payload


@dataclass(frozen=True)
class AgentChannelRoutingResult:
    protocol_version: str
    business_id: str
    channel_key: str
    message_hash: str
    normalized_intent_preview: Dict[str, Any]
    timeline_preview: Dict[str, Any]
    blocked_reasons: List[str]
    requires_human_review: bool = True
    dry_run_only: bool = True
    would_send_email: bool = False
    would_send_whatsapp: bool = False
    would_call_phone_provider: bool = False
    would_mutate_job_timeline: bool = False
    would_create_external_side_effect: bool = False
    created_at_ms: int = field(default_factory=_now_ms)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def list_agent_channels() -> Dict[str, Any]:
    channels = []
    for key in sorted(SUPPORTED_AGENT_CHANNELS):
        channels.append(
            AgentChannel(
                channel_key=key,
                display_name=key.replace("_", " ").title(),
                reserved_only=key not in PREVIEW_ENABLED_CHANNELS,
                preview_enabled=key in PREVIEW_ENABLED_CHANNELS,
            ).to_dict()
        )

    return {
        "ok": True,
        "protocol_version": AGENT_CHANNEL_PROTOCOL_VERSION,
        "channels": channels,
        "count": len(channels),
    }


def build_agent_inbox_message(
    *,
    message_id: str,
    business_id: str,
    channel_key: str,
    raw_subject: str = "",
    raw_body: str = "",
    sender_ref: str = "",
    job_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    message = AgentInboxMessage(
        message_id=message_id,
        business_id=business_id,
        channel_key=channel_key,
        raw_subject=raw_subject,
        raw_body=raw_body,
        sender_ref=sender_ref,
        job_id=job_id,
        metadata=dict(metadata or {}),
    )
    return message.to_dict()


def preview_agent_channel_message(
    *,
    business_id: str,
    channel_key: str,
    raw_subject: str = "",
    raw_body: str = "",
    sender_ref: str = "",
    job_id: Optional[str] = None,
    message_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blocked: List[str] = []

    business_id = str(business_id or "").strip()
    channel_key = str(channel_key or "").strip().lower()
    raw_subject = str(raw_subject or "")
    raw_body = str(raw_body or "")

    if not business_id:
        blocked.append("missing_business_id")

    if not channel_key:
        blocked.append("missing_channel_key")
    elif channel_key not in SUPPORTED_AGENT_CHANNELS:
        blocked.append("unsupported_channel")

    if channel_key in RESERVED_ONLY_CHANNELS:
        blocked.append("channel_reserved_only")

    if not raw_subject and not raw_body:
        blocked.append("missing_message_content")

    msg = AgentInboxMessage(
        message_id=message_id or f"agent_msg_{_stable_hash({'business_id': business_id, 'channel_key': channel_key, 'raw_subject': raw_subject, 'raw_body': raw_body})[:16]}",
        business_id=business_id,
        channel_key=channel_key,
        raw_subject=raw_subject,
        raw_body=raw_body,
        sender_ref=str(sender_ref or ""),
        job_id=job_id,
        metadata=dict(metadata or {}),
    ).to_dict()

    intent_type = "supplier_update" if channel_key == "supplier_email" else "customer_request"

    normalized_intent_preview = {
        "gateway_protocol_version": "aion.gateway.v0.1",
        "business_id": business_id,
        "source_channel": channel_key,
        "vertical_key": str((metadata or {}).get("vertical_key") or "home_repair"),
        "intent_type": intent_type,
        "raw_payload_ref": msg["message_id"],
        "normalized_payload": {
            "subject": raw_subject.strip(),
            "body_preview": raw_body.strip()[:500],
            "sender_ref": str(sender_ref or ""),
            "job_id": job_id,
        },
        "requires_human_review": True,
        "dry_run_only": True,
    }
    normalized_intent_preview["intent_hash"] = _stable_hash(normalized_intent_preview)

    timeline_preview = {
        "would_attach_to_job_id": job_id,
        "timeline_event_type": "agent_channel_message_received",
        "message_hash": msg["message_hash"],
        "would_mutate_job_timeline": False,
        "append_only_preview": True,
    }

    result = AgentChannelRoutingResult(
        protocol_version=AGENT_CHANNEL_PROTOCOL_VERSION,
        business_id=business_id,
        channel_key=channel_key,
        message_hash=msg["message_hash"],
        normalized_intent_preview=normalized_intent_preview,
        timeline_preview=timeline_preview,
        blocked_reasons=blocked,
    ).to_dict()

    result["message"] = msg
    result["ok"] = len(blocked) == 0
    result["routing_status"] = "preview_ready" if result["ok"] else "blocked"
    return result
