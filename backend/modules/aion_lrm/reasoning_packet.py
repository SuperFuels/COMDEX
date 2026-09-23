from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import hashlib
import json


AION_REASONING_PACKET_VERSION = "aion.reasoning_packet.v0.1"


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class AionReasoningSafety:
    preview_only: bool = True
    human_review_required: bool = True
    booking_created: bool = False
    payment_created: bool = False
    escrow_created: bool = False
    external_message_sent: bool = False
    live_chain_write: bool = False
    raw_tool_execution: bool = False
    automatic_memory_mutation: bool = False
    goal_engine_executed: bool = False
    workflow_executed_live: bool = False


@dataclass(frozen=True)
class AionReasoningPacket:
    packet_version: str
    business_id: str
    vertical_key: str
    source: str
    website_intake: Dict[str, Any] = field(default_factory=dict)
    commercial_ticket: Dict[str, Any] = field(default_factory=dict)
    workflow_context: Dict[str, Any] = field(default_factory=dict)
    agentmap_context: Dict[str, Any] = field(default_factory=dict)
    boardroom_context: Dict[str, Any] = field(default_factory=dict)
    proof_context: Dict[str, Any] = field(default_factory=dict)
    ets_context: Dict[str, Any] = field(default_factory=dict)
    safety: AionReasoningSafety = field(default_factory=AionReasoningSafety)
    risk_level: str = "human_review_required"
    recommended_next_action: str = "prepare_founder_review"
    reasoning_notes: List[str] = field(default_factory=list)
    blocked_reasons: List[str] = field(default_factory=list)
    reasoning_packet_hash: Optional[str] = None
    summary_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["safety"] = asdict(self.safety)

        unsigned = {
            k: v
            for k, v in payload.items()
            if k not in {"reasoning_packet_hash", "summary_hash"}
        }

        summary = {
            "packet_version": self.packet_version,
            "business_id": self.business_id,
            "vertical_key": self.vertical_key,
            "source": self.source,
            "risk_level": self.risk_level,
            "recommended_next_action": self.recommended_next_action,
            "preview_only": self.safety.preview_only,
            "human_review_required": self.safety.human_review_required,
        }

        payload["reasoning_packet_hash"] = self.reasoning_packet_hash or _stable_hash(unsigned)
        payload["summary_hash"] = self.summary_hash or _stable_hash(summary)
        return payload


def build_aion_reasoning_packet(
    *,
    business_id: str,
    vertical_key: str,
    source: str,
    website_intake: Optional[Dict[str, Any]] = None,
    commercial_ticket: Optional[Dict[str, Any]] = None,
    workflow_context: Optional[Dict[str, Any]] = None,
    agentmap_context: Optional[Dict[str, Any]] = None,
    boardroom_context: Optional[Dict[str, Any]] = None,
    proof_context: Optional[Dict[str, Any]] = None,
    ets_context: Optional[Dict[str, Any]] = None,
    recommended_next_action: str = "prepare_founder_review",
    reasoning_notes: Optional[List[str]] = None,
    blocked_reasons: Optional[List[str]] = None,
) -> Dict[str, Any]:
    packet = AionReasoningPacket(
        packet_version=AION_REASONING_PACKET_VERSION,
        business_id=business_id.lower().strip(),
        vertical_key=vertical_key.lower().strip(),
        source=source,
        website_intake=website_intake or {},
        commercial_ticket=commercial_ticket or {},
        workflow_context=workflow_context or {},
        agentmap_context=agentmap_context or {},
        boardroom_context=boardroom_context or {},
        proof_context=proof_context or {},
        ets_context=ets_context or {},
        recommended_next_action=recommended_next_action,
        reasoning_notes=reasoning_notes or [],
        blocked_reasons=blocked_reasons or [],
    )
    return packet.to_dict()


def build_home_fixed_reasoning_packet_preview() -> Dict[str, Any]:
    return build_aion_reasoning_packet(
        business_id="home_fixed",
        vertical_key="home_repair",
        source="home_fixed_website_widget_preview",
        website_intake={
            "customer_message": "Leaking pergola roof in Arboleas after rain",
            "detected_service": "pergola_roof_repair",
            "location": "Arboleas",
            "urgency": "medium",
            "channel": "website_widget",
        },
        commercial_ticket={
            "route_type": "custom_quote",
            "pricing_model": "inspection_required",
            "quote_preview": "EUR 120-380 preview range",
            "final_quote_created": False,
        },
        workflow_context={
            "workflow_id": "home_fixed_new_enquiry",
            "workflow_mode": "guarded_preview",
            "workflow_executed_live": False,
        },
        agentmap_context={
            "agentmap_route": "home_repair.quote_preview",
            "agentmap_verified_preview": True,
            "safe_for_agent_discovery": True,
        },
        boardroom_context={
            "surface": "parallel_twin_founder_demo",
            "visible_to_founder": True,
            "human_review_handoff": True,
        },
        proof_context={
            "proof_receipt_preview": True,
            "glyphchain_live_write": False,
            "proof_hash_available": True,
        },
        ets_context={
            "ets_preview": True,
            "customer_outcome_score": None,
            "system_execution_score": None,
            "live_reputation_mutation": False,
        },
        recommended_next_action="show_founder_review_and_proof_preview",
        reasoning_notes=[
            "Website intake can become a guarded business ticket.",
            "Commercial ticket requires human review before any live quote or booking.",
            "Proof and ETS remain preview-only.",
        ],
        blocked_reasons=[
            "booking_requires_human_approval",
            "payment_disabled",
            "escrow_disabled",
            "external_messages_disabled",
            "live_chain_write_disabled",
        ],
    )
